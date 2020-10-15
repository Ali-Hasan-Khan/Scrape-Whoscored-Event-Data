# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:28:34 2020

@author: aliha
@twitter: rockingAli5 
"""

"""
A tutorial on getting Event Data for a single match, 
with an example of Passing Network for a team.
"""



import pandas as pd
import numpy as np
from selenium import webdriver
from main import (getMatchData,  createMatchesDF, createEventsDF)
from visuals import createPassNetworks




# Get Match Data  (Run from line 29 to line 35 together)   
if __name__ == "__main__":
    driver = webdriver.Chrome('chromedriver.exe')
    
    
# whoscored match centre url of the required match (Example: Barcelona vs Sevilla)
url = "https://www.whoscored.com/Matches/1491995/Live/Spain-LaLiga-2020-2021-Barcelona-Sevilla"
match_data = getMatchData(driver, url)


# Match dataframe containing info about the match
matches_df = createMatchesDF(match_data)


# Events dataframe      
events_df = createEventsDF(match_data)


# match Id
matchId = match_data['matchId']


# Information about respective taems as dictionary
home_data = matches_df['home'][matchId]
away_data = matches_df['away'][matchId]



# Pass Network Example from Barcelona vs Sevilla game     
team = 'Barcelona'
teamId = 65
opponent = 'Sevilla'
venue = 'home'

# Create Pass Network     
createPassNetworks(matches_df, events_df, matchId, teamId, team, opponent, venue)








