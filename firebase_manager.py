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