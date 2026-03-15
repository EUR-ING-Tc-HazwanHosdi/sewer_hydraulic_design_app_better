Sewer Hydraulic Design Software

How to run:
1. Install Python 3.10+.
2. Open terminal in this folder.
3. Install packages:
   pip install -r requirements.txt
4. Run the app:
   streamlit run app.py

What this software does:
- Upload an Excel sewer design file
- Change diameter, gradient, and flow per PE
- View velocity chart, design flow chart, and 3D sewer surface
- Check whether velocity is within 0.8 to 4.0 m/s
- Download recalculated results as CSV

Required Excel columns:
- Manhole
- PE_on_Line
- Peak_Factor
