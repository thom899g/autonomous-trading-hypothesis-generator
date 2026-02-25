# Autonomous Trading Hypothesis Generator

## Objective
An AI system designed to autonomously generate and test innovative trading strategies, enhancing decision-making processes and driving efficiency in the market.

## Strategy
Implement advanced machine learning models to create hypotheses, integrate backtesting frameworks for evaluation, develop APIs for live trading integration, and continuously refine strategies based on performance metrics.

## Execution Output
SUMMARY: I created a comprehensive autonomous trading hypothesis generator system with robust architecture, featuring strategy generation, backtesting, portfolio management, and real-time Firebase integration. The system handles market data, generates ML-based trading signals, performs rigorous backtesting with risk metrics, and stores all results in Firestore for state persistence.

OUTPUT:

### FILE: requirements.txt
```
# Trading Hypothesis Generator
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
ccxt>=4.0.0
yfinance>=0.2.0
ta>=0.10.0
firebase-admin>=6.3.0
schedule>=1.2.0
python-dotenv>=1.0.0
loguru>=0.7.0
pytest>=7.4.0
pandas-ta>=0.3.14
```

### FILE: .env
```
# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY=your-private-key
FIREBASE_CLIENT_EMAIL=your-client-email
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_CLIENT_X509_CERT_URL=your-cert-url

# Trading Configuration
MAX_POSITION_SIZE=0.1  # 10% of portfolio per trade
MAX_DRAWDOWN=0.25      # 25% max drawdown
RISK_FREE_RATE=0.02    # 2% annual risk-free rate
INITIAL_CAPITAL=100000 # $100k starting capital
```

### FILE: firebase_manager.py
```python
"""
Firebase Manager for Trading Ecosystem
Handles all Firestore operations for strategy persistence, backtest results,
and real-time state management.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import Client as FirestoreClient
from loguru import logger

class StrategyStatus(Enum):
    """Status of trading strategies"""
    GENERATED = "generated"
    BACKTESTING = "backtesting"
    BACKTESTED = "backtested"
    LIVE_PAPER = "live_paper"
    LIVE_PRODUCTION = "live_production"
    ARCHIVED = "archived"

@dataclass
class StrategyMetadata:
    """Metadata for trading strategies"""
    strategy_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    status: StrategyStatus
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    total_return: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Firestore-compatible dictionary"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyMetadata':
        """Create from Firestore dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['status'] = StrategyStatus(data['status'])
        return cls(**data)

class FirebaseManager:
    """Manages all Firebase Firestore operations"""
    
    _instance: Optional['FirebaseManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize_firebase()
            self._initialized = True
    
    def _initialize_firebase(self) -> None:
        """Initialize Firebase with environment credentials"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Parse private key from environment
                private_key = os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
                
                cred_dict = {
                    "type": "service_account",
                    "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                    "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                    "private_key": private_key,
                    "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
                    "client_id": os.getenv('FIREBASE_CLIENT_ID'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
                }
                
                # Filter out None values
                cred_dict = {k: v for k, v in cred_dict.items() if v is not None}
                
                if not all(cred_dict.values()):
                    raise ValueError("Missing Firebase environment variables")
                
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            
            self.db: FirestoreClient = firestore.client()
            logger.success("Firebase Firestore initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    def save_strategy(self, strategy_metadata: StrategyMetadata) -> bool:
        """Save strategy metadata to Firestore"""
        try:
            strategy_ref = self.db.collection('strategies').document(strategy_metadata.strategy_id)
            strategy_ref.set(strategy_metadata.to_dict())
            logger.info(f"Strategy {strategy_metadata.strategy_id} saved to Firestore")
            return True
        except Exception as e:
            logger.error(f"Failed to save strategy: {e}")
            return False
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """Retrieve strategy metadata from Firestore"""
        try:
            strategy_ref = self.db.collection('strategies').document(strategy_id)
            strategy_data = strategy_ref.get()
            
            if strategy_data.exists:
                return StrategyMetadata.from_dict(strategy_data.to_dict())
            else:
                logger.warning(f"Strategy {strategy_id} not found in Firestore")
                return None
        except Exception as e:
            logger.error(f"Failed to get strategy: {e}")
            return None
    
    def update_strategy_status(self