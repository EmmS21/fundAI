exam-assistant/
├── src/
│   ├── main.py                
│   │
│   ├── data/
│   │   ├── cache/
│   │   │   ├── metadata/       
│   │   │   └── responses/    
│   │   ├── database/
│   │   │   ├── models.py      
│   │   │   └── operations.py  
│   │
│   ├── core/
│   │   ├── network/
│   │   │   └── sync_service.py 
│   │   │
│   │   ├── queue_manager.py    
│   │   └── firebase/
│   │       └── client.py       
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
│   │   └── constants.py        
│   │
│   └── config/
│       └── firebase_config.py  
│
└── student_profile.db         