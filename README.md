# BGU Mobility Survey Analysis

This project analyzes mobility survey data from BGU students, focusing on transportation patterns, route choices, and points of interest.


## Survey Variable Index

| Variable Name | Description | Values/Scale |
|---------------|-------------|--------------|
| **Residence-Info** | P2 Q1 היכן את\ה גר\ה? (Where do you live?) | Map Coordinates and text |
| **Transportation-Mode** | P2 Q2 באיזה אמצעי תחבורה את\ה בדרך כלל משתמש\ת כדי להגיע מהבית לאוניברסיטה? (Which transportation mode do you usually use to get from home to university?) | 1=Walking, 2=Electric Bicycle/Scooter, 3=Car, 4=Bicycle, 5=Bus, 6=Horseback riding, 7=Other |
| **Routechoice-Distance** | P2 Q3 מרחק (Distance considerations in route choice) | 1-5 scale (importance ranking) |
| **Routechoice-Time** | P2 Q3 זמן (Time considerations in route choice) | 1-5 scale (importance ranking) |
| **Routechoice-Shadow** | P2 Q3 צל (Shade considerations in route choice) | 1-5 scale (importance ranking) |
| **Routechoice-Stores** | P2 Q3 חנויות (Store access considerations in route choice) | 1-5 scale (importance ranking) |
| **Routechoice-Friends** | P2 Q3 חברים (Meeting friends considerations in route choice) | 1-5 scale (importance ranking) |
| **Routechoice-Convenience** | P2 Q3 נוחות (Convenience considerations in route choice) | 1-5 scale (importance ranking) |
| **Routechoice-Work** | P2 Q3 עבודה (Work-related considerations in route choice) | 1-5 scale (importance ranking) |
| **Distance-Perception** | P2 Q4 עד כמה קרוב\רחוק את.ה מרגיש.ה שאת.ה גר.ה מהאוניברסיטה? (How close/far do you feel you live from the university?) | 1-5 scale (1=close, 5=far) |
| **Challenges** | P2 Q5 מהם האתגרים העיקריים בהם את.ה נתקל.ת בדרכך לאוניברסיטה? (Main challenges on your way to university) | Free text |
| **Suggestions** | P2 Q6 אילו שינויים באזור האוניברסיטה ישפרו את הדרך שלך? (What changes in the university area would improve your journey?) | Free text |
| **POI** | P2 Q7 סמן.י על המפה 3 נקודות עניין (Mark 3 points of interest on your route) | Map coordinates and text |
| **Further-yes** | P3 Q1 כן אשמח (Yes, I'd be happy to participate in a more detailed survey) | Binary (Yes/Empty) |
| **Further-no** | P3 Q1 לא תודה (No thank you for detailed survey) | Binary (No/Empty) |
| **FurtherWeek-yes** | P3 Q2 אשמח מאוד לקחת חלק במחקר (Yes, I'd love to participate in week-long tracking study) | Binary (Yes/Empty) |
| **FurtherWeek-no** | P3 Q2 לא תודה, אמשיך הלאה בחיי (No thank you for tracking study) | Binary (No/Empty) |
| **FurtherWeek-other** | P3 Q2 Other response for tracking study | Free text |


## Visualizations

All visualizations are exported as HTML with dark mode styling using modern libraries:
- Maps: Deck.gl for interactive geographic visualizations
- Charts: Plotly/Chart.js for interactive charts
- Dashboard: Combined interface for all analyses