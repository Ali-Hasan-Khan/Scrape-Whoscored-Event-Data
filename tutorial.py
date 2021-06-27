# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:28:34 2020

@author: aliha
@twitter: @rockingAli5 
"""

"""
Tutorial on getting hands on the event data for a single match.

New: Now added xG data for shots from Understat.com(only available for top 5 european leagues since 2014-15).
"""


import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from selenium import webdriver
import main
import visuals
import seaborn as sns





###     Get Match Data  (Run from line 29 to line 35 together)      ###         
if __name__ == "__main__":
    driver = webdriver.Chrome('chromedriver.exe')
    
# whoscored match centre url of the required match (Example: Barcelona vs Sevilla)
url = "https://www.whoscored.com/Matches/1491995/Live/Spain-LaLiga-2020-2021-Barcelona-Sevilla"
match_data = main.getMatchData(driver, url, close_window=True)

# Match dataframe containing info about the match
matches_df = main.createMatchesDF(match_data)

# Events dataframe      
events_df = main.createEventsDF(match_data)

# match Id
matchId = match_data['matchId']

# Information about respective teams as dictionary
home_data = matches_df['home'][matchId]
away_data = matches_df['away'][matchId]





###     Get EPV for successful passes     ###
events_df = main.addEpvToDataFrame(events_df)





###    Get data for multiple matches    ###  
# getting competition urls
league_urls = main.getLeagueUrls()

# getting match urls for that competition and season
match_urls = main.getMatchUrls(comp_url=league_urls['LaLiga'], season='2020/2021')

# getting match urls for a specific team
team_urls = main.getTeamUrls(team='Barcelona', match_urls=match_urls)

# getting match data for the required urls(eg. first 5 matches of Barcelona)
matches_data = main.getMatchesData(match_urls=team_urls[:5])

# getting events dataframe for required matches
events_ls = [main.createEventsDF(match) for match in matches_data]

# adding EPV column
events_list = [main.addEpvToDataFrame(match) for match in events_ls]
events_dfs = pd.concat(events_list)

# saving events as csv
events_dfs.to_csv('events.csv')





###     Pass Network Examples from Barcelona vs Sevilla game     ###
team = 'Barcelona'
teamId = 65
opponent = 'Sevilla'
venue = 'home'

team_players_dict = {}
for player in matches_df['home'][match_data['matchId']]['players']:
    team_players_dict[player['playerId']] = player['name'] 
    
# Total Passes
passes_df = events_df.loc[events_df['type']=='Pass'].reset_index(drop=True)
passes_df = passes_df.loc[passes_df['outcomeType']=='Successful'].reset_index(drop=True)
passes_df = passes_df.loc[passes_df['teamId'] == teamId].reset_index(drop=True)





###     Get Passes For Different Durations     ###
# Cut in 2
first_half_passes = passes_df.loc[passes_df['period']=='FirstHalf']
second_half_passes = passes_df.loc[passes_df['period']=='SecondHalf'].reset_index(drop=True)

# Cut in 4 (quarter = 25 mins)
first_quarter_passes = first_half_passes.loc[first_half_passes['minute'] <= 25]
second_quarter_passes = first_half_passes.loc[first_half_passes['minute'] > 25].reset_index(drop=True)
third_quarter_passes = second_half_passes.loc[second_half_passes['minute'] <= 70]
fourth_quarter_passes = second_half_passes.loc[second_half_passes['minute'] > 70].reset_index(drop=True)





###     Get Team Total Passes     ###
visuals.getTeamTotalPasses(events_df, teamId, team, opponent, pitch_color='#000000')





###     Get Completed Box Passes by Team    ###
# You can select more cmaps here: https://matplotlib.org/3.1.0/tutorials/colors/colormaps.html
# opp_transparent/opp_comet are manually added by me to this visual, you can change it in visuals.py
# If you get an error regarding 'opp_transparent/opp_comet' you probably haven't replaced pitch.py/linecollection.py file
visuals.getTeamSuccessfulBoxPasses(events_df, teamId, team, pitch_color='#000000', cmap='YlGn')





# Create Pass Network
# you can change marker_label to 'name' as well
fig,ax = plt.subplots(figsize=(16,11))
visuals.createPassNetworks(match_data, events_df, matchId=match_data['matchId'], team='Barcelona', max_line_width=6, 
                           marker_size=1500, edgewidth=3, dh_arrow_width=25, marker_color='#0e5cba',
                           marker_edge_color='w', shrink=24, ax=ax, kit_no_size=25)



# Create Progressive Pass Network
# you can change marker_label to 'name' as well
fig,ax = plt.subplots(figsize=(16,11))
visuals.createAttPassNetworks(match_data, events_df, matchId=match_data['matchId'], team='Barcelona', max_line_width=6, 
                              marker_size=1300, edgewidth=3, dh_arrow_width=25, marker_color='#0e5cba', 
                              marker_edge_color='w', shrink=24, ax=ax, kit_no_size=25)






###    Get Shot map for a team    ###
fig,ax = plt.subplots(figsize=(16,11))
visuals.createShotmap(match_data, events_df, team='Barcelona', pitchcolor='black', shotcolor='white', 
                      goalcolor='red', titlecolor='white', legendcolor='white', marker_size=300, fig=fig, ax=ax)





###    Get Net PV formation map for a team    ###
# Choose your color palette from here: https://seaborn.pydata.org/tutorial/color_palettes.html
fig,ax = plt.subplots(figsize=(16,11))
visuals.createPVFormationMap(match_data, events_df, team='Barcelona', color_palette=sns.color_palette("flare", as_cmap=True),
                             markerstyle='h', markersize=1000, markeredgewidth=2, labelsize=7, labelcolor='w', ax=ax)

















