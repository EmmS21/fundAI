exam-assistant/
├── src/
│   ├── main.py                
│   │
│   ├── data/
│   │   ├── cache/
│   │   │   ├── metadata/       # Stores metadata for cached questions
│   │   │   ├── responses/      
│   │   │   └── cache_manager.py # Updated to handle questions with assets
│   │   ├── database/
│   │   │   ├── models.py      
│   │   │   └── operations.py  
│   │
│   ├── core/
│   │   ├── network/
│   │   │   ├── sync_service.py        # Updated to handle question syncing
│   │   │   └── network_monitor.py     # Monitors network connectivity
│   │   │
│   │   ├── queue_manager.py           # Enhanced with batch processing
│   │   └── firebase/
│   │       └── client.py              # Enhanced with batch operations
│   │
│   ├── ui/
│   │   └── components/
│   │       ├── onboarding/
│   │       │   └── onboarding_window.py  
│   │       │
│   │       └── profile/
│   │           ├── profile_info_widget.py 
│   │           ├── subjects/
│   │           │   ├── subject_selector.py 
│   │           │   └── subject_card.py     
│   │           │
│   │           └── achievements/
│   │               └── achievement_widget.py 
│   │
│   ├── utils/
│   │   ├── db.py              
│   │   ├── constants.py        
│   │   └── hardware_identifier.py  # For generating unique device IDs
│   │
│   └── config/
│       └── firebase_config.py  
│
└── student_profile.db         