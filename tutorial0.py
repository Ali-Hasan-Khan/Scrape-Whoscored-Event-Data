# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:28:34 2020

@author: aliha
@twitter: rockingAli5 
"""


import pandas as pd
import numpy as np
from mplsoccer.pitch import Pitch
from matplotlib.colors import to_rgba
from selenium import webdriver

from main import (getLeagueLinks, getMatchData, getMatchLinks, getTeamData, getTeamLinks,
                  createMatchesDF, createEventsDF)

from visuals import createPassNetworks




###     Get Match Data     ###
if __name__ == "__main__":
    driver = webdriver.Chrome('chromedriver.exe')
# whoscored url to the required match
url = "https://www.whoscored.com/Matches/1491995/Live/Spain-LaLiga-2020-2021-Barcelona-Sevilla"
match_data = getMatchData(driver, url)


matches_df = createMatchesDF(match_data)
events_df = createEventsDF(match_data)




###     Create Pass Network     ###

team = 'Barcelona'
teamId = 65
opponent = 'Sevilla'
matchId = match_data['matchId']
venue = 'home'


createPassNetworks(matches_df, events_df, matchId, teamId, team, opponent, venue)








