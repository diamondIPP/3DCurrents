# Small script to plot the currents from the RD42 3D cern beam test!

Requirements:
- python 2.6
- matplotlib 0.99

1. (if not already existant) create the run_log.json file with the createRunList.py* script!
2. execute '''./3DCurrents.py <run_nr> (<end_run>) -d <hv_data_dir>'''

--> see '''./3DCurrents.py -h for help!'''

 createRunList.py: independent script to create a json run log based on the time stamps of the date files and Harris' run log 
