# Medal criteria
MEDAL_CRITERIA = {
    'gold': {'threshold': 90, 'description': 'Achieved 90% or higher'},
    'silver': {'threshold': 75, 'description': 'Achieved 75% or higher'},
    'bronze': {'threshold': 60, 'description': 'Achieved 60% or higher'}
}

# Medal colors
MEDAL_COLORS = {
    'gold': '#FFD700',   
    'silver': '#C0C0C0', 
    'bronze': '#CD7F32'  
}

# Medal styles
MEDAL_STYLE = """
    QWidget#medal-container {{
        background-color: {color};
        border-radius: 25px;
        min-width: 50px;
        min-height: 50px;
        max-width: 50px;
        max-height: 50px;
    }}
    
    QLabel#medal-count {{
        color: #1a1a1a;
        font-size: 16px;
        font-weight: bold;
    }}
    
    QLabel#medal-label {{
        color: #666666;
        font-size: 14px;
    }}
"""
