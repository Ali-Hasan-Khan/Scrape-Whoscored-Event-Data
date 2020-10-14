# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:38:46 2020

@author: aliha
@twitter: rockingAli5 
"""

import pandas as pd
import numpy as np
from mplsoccer.pitch import Pitch
from matplotlib.colors import to_rgba



def createPassNetworks(matches_df, events_df, matchId, teamId, team, opponent, venue):
    team_players_dict = {}
    for player in matches_df[venue][matchId]['players']:
        team_players_dict[player['playerId']] = player['name']
    
    match_events_df = events_df.loc[events_df['matchId'] == matchId].reset_index(drop=True)
    passes_df = match_events_df.loc[[row['displayName'] == 'Pass' for row in list(match_events_df['type'])]].reset_index(drop=True)
    passes_df = passes_df.loc[passes_df['teamId'] == teamId].reset_index().drop('index', axis=1)
    passes_df = passes_df.loc[[row['displayName'] == 'Successful' for row in list(passes_df['outcomeType'])]].reset_index(drop=True)
    
    
            
    passes_df.insert(27, column='playerName', value=[team_players_dict[i] for i in list(passes_df['playerId'])])
    passes_df.insert(28, column='passRecipientId', value=passes_df['playerId'].shift(-1))  
    passes_df.insert(29, column='passRecipientName', value=passes_df['playerName'].shift(-1))  
    passes_df.dropna(subset=["passRecipientName"], inplace=True)
    
    match_players_df = pd.DataFrame()
    player_names = []
    player_ids = []
    player_pos = []
    player_kit_number = []
    
    
    for player in matches_df[venue][matchId]['players']:
                player_names.append(player['name'])
                player_ids.append(player['playerId'])
                player_pos.append(player['position'])
                player_kit_number.append(player['shirtNo'])
                
    match_players_df['playerId'] = player_ids
    match_players_df['playerName'] = player_names
    match_players_df['playerPos'] = player_pos
    match_players_df['playerKitNumber'] = player_kit_number

    passes_df = passes_df.merge(match_players_df, on=['playerId', 'playerName'], how='left', validate='m:1')
    passes_df = passes_df.merge(match_players_df.rename({'playerId': 'passRecipientId', 'playerName':'passRecipientName'},
                                                        axis='columns'), on=['passRecipientId', 'passRecipientName'],
                                                        how='left', validate='m:1', suffixes=['', 'Receipt'])
    passes_df = passes_df[passes_df['playerPos'] != 'Sub']
    passes_formation = passes_df[['id', 'playerKitNumber', 'playerKitNumberReceipt']].copy()
    location_formation = passes_df[['playerKitNumber', 'x', 'y']]
    
    average_locs_and_count = location_formation.groupby('playerKitNumber').agg({'x': ['mean'], 'y': ['mean', 'count']})
    average_locs_and_count.columns = ['x', 'y', 'count']
    
    passes_formation['kitNo_max'] = passes_formation[['playerKitNumber',
                                                    'playerKitNumberReceipt']].max(axis='columns')
    passes_formation['kitNo_min'] = passes_formation[['playerKitNumber',
                                                    'playerKitNumberReceipt']].min(axis='columns')
    
    
    passes_between = passes_formation.groupby(['kitNo_max', 'kitNo_min']).id.count().reset_index()
    passes_between.rename({'id': 'pass_count'}, axis='columns', inplace=True)
    
    # add on the location of each player so we have the start and end positions of the lines
    passes_between = passes_between.merge(average_locs_and_count, left_on='kitNo_min', right_index=True)
    passes_between = passes_between.merge(average_locs_and_count, left_on='kitNo_max', right_index=True,
                                          suffixes=['', '_end'])
    
    ##############################################################################
    # Calculate the line width and marker sizes relative to the largest counts
    
    max_line_width = 18
    marker_size = 2000
    passes_between['width'] = passes_between.pass_count / passes_between.pass_count.max() * max_line_width
    #average_locs_and_count['marker_size'] = (average_locs_and_count['count']
    #                                         / average_locs_and_count['count'].max() * max_marker_size)
    
    ##############################################################################
    # Set color to make the lines more transparent when fewer passes are made
    
    min_transparency = 0.3
    color = np.array(to_rgba('white'))
    color = np.tile(color, (len(passes_between), 1))
    c_transparency = passes_between.pass_count / passes_between.pass_count.max()
    c_transparency = (c_transparency * (1 - min_transparency)) + min_transparency
    color[:, 3] = c_transparency
    
    ##############################################################################
    # Plotting
    
    
    pitch = Pitch(pitch_type='statsbomb', orientation='horizontal',
                  pitch_color='#000000', line_color='#c7d5cc', figsize=(16, 11),
                  constrained_layout=True, tight_layout=False)
    fig, ax = pitch.draw()
    pitch.lines(passes_between.x/100*120, 80-passes_between.y/100*80,
                passes_between.x_end/100*120, 80-passes_between.y_end/100*80, lw=passes_between.width,
                color=color, zorder=1, ax=ax)
    pitch.scatter(average_locs_and_count.x/100*120, 80-average_locs_and_count.y/100*80, s=marker_size,
                  color='#6a009c', edgecolors='black', linewidth=1, alpha=1, ax=ax)
    for index, row in average_locs_and_count.iterrows():
        pitch.annotate(row.name, xy=(row.x/100*120, 80-row.y/100*80), c='white', va='center', ha='center', size=20, weight='bold', ax=ax)
    ax.set_title("{} Pass Network vs {}".format(team, opponent), size=15, y=0.97, color='#c7d5cc')
    fig.set_facecolor("#000000")
    #plt.savefig(f'visualisations\{team} Pass Network vs {opponent}.png', facecolor=fig.get_facecolor(), edgecolor='none')



