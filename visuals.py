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


def createShotmap(match_data, events_df, team, pitchcolor, shotcolor, goalcolor, titlecolor, legendcolor, marker_size):
    # getting team id and venue
    if match_data['home']['name'] == team:
        teamId = match_data['home']['teamId']
        venue = 'home'
    else:
        teamId = match_data['away']['teamId']
        venue = 'away'
        
    # getting opponent   
    if venue == 'home':
        opponent = match_data['away']['name']
    else:
        opponent = match_data['home']['name']
        
    total_shots = events_df.loc[[9 in row for row in list(events_df['satisfiedEventsTypes'])]]
    team_shots = total_shots.loc[total_shots['teamId'] == teamId].reset_index(drop=True)
    mask_goal = team_shots.isGoal == True

    # Setup the pitch
    pitch = Pitch(pitch_type='statsbomb', orientation='vertical', pitch_color=pitchcolor, line_color='#c7d5cc',
                  figsize=(16, 11), view='half', pad_top=2, tight_layout=True)
    fig, ax = pitch.draw()


    # Plot the goals
    pitch.scatter(team_shots[mask_goal].x/100*120, 80-team_shots[mask_goal].y/100*80, s=marker_size,
                  edgecolors='black', c=goalcolor, zorder=2,
                  label='goal', ax=ax)
    pitch.scatter(team_shots[~mask_goal].x/100*120, 80-team_shots[~mask_goal].y/100*80,
                  edgecolors='white', c=shotcolor, s=marker_size, zorder=2,
                  label='shot', ax=ax)
    # Set the title
    ax.set_title(f'{team} shotmap \n vs {opponent}', fontsize=30, color=titlecolor)

    # set legend
    leg = ax.legend(facecolor=pitchcolor, edgecolor='None', fontsize=20, loc='lower center', handlelength=4)
    leg_texts = leg.get_texts() # list of matplotlib Text instances.
    leg_texts[0].set_color(legendcolor)
    leg_texts[1].set_color(legendcolor)
    
    # Set the figure facecolor
    fig.set_facecolor(pitchcolor)
    
    
    
    


def createPassNetworks(match_data, matches_df, events_df, team,
                       pitch_color, max_lw, marker_size, marker_color):
    """
    

    Parameters
    ----------
    match_data : Data containing everything about the match
    
    matches_df : DataFrame containing match data.
    
    events_df : DataFrame containing event data for that match.
    
    team : Name of the required team.
    
    pitch_color : color of the pitch and figure.
    
    max_lw : maximum line width of network lines.
    
    marker_size : size of the circle markers.
    
    marker_color : color of the circle markers.
    
    
    Returns
    -------
    Pitch Plot.
    """
    
    matchId = match_data['matchId']

    
    # getting team id and venue
    if match_data['home']['name'] == team:
        teamId = match_data['home']['teamId']
        venue = 'home'
    else:
        teamId = match_data['away']['teamId']
        venue = 'away'
        
    # getting opponent   
    if venue == 'home':
        opponent = match_data['away']['name']
    else:
        opponent = match_data['home']['name']
    
    team_players_dict = {}
    for player in matches_df[venue][matchId]['players']:
        team_players_dict[player['playerId']] = player['name']
    
    passes_df = events_df.loc[[row['displayName'] == 'Pass' for row in list(events_df['type'])]].reset_index(drop=True)
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
    
    max_line_width = max_lw
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
                  pitch_color=pitch_color, line_color='#c7d5cc', figsize=(16, 11),
                  constrained_layout=True, tight_layout=False)
    fig, ax = pitch.draw()
    pitch.lines(passes_between.x/100*120, 80-passes_between.y/100*80,
                passes_between.x_end/100*120, 80-passes_between.y_end/100*80, lw=passes_between.width,
                color=color, zorder=1, ax=ax)
    pitch.scatter(average_locs_and_count.x/100*120, 80-average_locs_and_count.y/100*80, s=marker_size,
                  color=marker_color, edgecolors='black', linewidth=1, alpha=1, ax=ax)
    for index, row in average_locs_and_count.iterrows():
        pitch.annotate(row.name, xy=(row.x/100*120, 80-row.y/100*80), c='white', va='center', ha='center', size=20, weight='bold', ax=ax)
    ax.set_title("{} Pass Network vs {}".format(team, opponent), size=15, y=0.97, color='#c7d5cc')
    fig.set_facecolor(pitch_color)
    #plt.savefig(f'visualisations\{team} Pass Network vs {opponent}.png', facecolor=fig.get_facecolor(), edgecolor='none')



    
    
    
    
    
    
def createAttPassNetworks(match_data, matches_df, events_df, team, pitch_color, max_lw, 
                          marker_size, marker_color):
    
    """
    

    Parameters
    ----------
    match_data : Data containing everything about the match
    
    matches_df : DataFrame containing match data.
    
    events_df : DataFrame containing event data for that match.
    
    team : Name of the required team.
    
    pitch_color : color of the pitch and figure.
    
    max_lw : maximum line width of network lines.
    
    marker_size : size of the circle markers.
    
    marker_color : color of the circle markers.

    
    Returns
    -------
    Pitch Plot.
    """
        
        
    # getting match_id
    matchId = match_data['matchId']
    
    
    # getting team id and venue
    if match_data['home']['name'] == team:
        teamId = match_data['home']['teamId']
        venue = 'home'
    else:
        teamId = match_data['away']['teamId']
        venue = 'away'
    
    
    # getting opponent   
    if venue == 'home':
        opponent = match_data['away']['name']
    else:
        opponent = match_data['home']['name']
    
    
    # getting player dictionary
    team_players_dict = {}
    for player in match_data[venue]['players']:
        team_players_dict[player['playerId']] = player['name']
    
    
    # getting minute of first substitution
    for i,row in events_df.iterrows():
        if row['type']['displayName'] == 'SubstitutionOn' and row['teamId'] == teamId:
            sub_minute = str(row['minute'])
            break
    
    
    # getting players dataframe
    match_players_df = pd.DataFrame()
    player_names = []
    player_ids = []
    player_pos = []
    player_kit_number = []


    for player in match_data[venue]['players']:
        player_names.append(player['name'])
        player_ids.append(player['playerId'])
        player_pos.append(player['position'])
        player_kit_number.append(player['shirtNo'])

    match_players_df['playerId'] = player_ids
    match_players_df['playerName'] = player_names
    match_players_df['playerPos'] = player_pos
    match_players_df['playerKitNumber'] = player_kit_number
    
    
    # extracting passes
    passes_df = events_df.loc[events_df['teamId'] == teamId].reset_index().drop('index', axis=1)
    passes_df.dropna(subset=["playerId"], inplace=True)
    passes_df.insert(27, column='playerName', value=[team_players_dict[i] for i in list(passes_df['playerId'])])
    passes_df.insert(28, column='passRecipientId', value=passes_df['playerId'].shift(-1))  
    passes_df.insert(29, column='passRecipientName', value=passes_df['playerName'].shift(-1))  
    passes_df.dropna(subset=["passRecipientName"], inplace=True)
    passes_df = passes_df.loc[[row['displayName'] == 'Pass' for row in list(passes_df['type'])]].reset_index(drop=True)
    passes_df = passes_df.loc[[row['displayName'] == 'Successful' for row in list(passes_df['outcomeType'])]].reset_index(drop=True)
    index_names = passes_df.loc[passes_df['playerName']==passes_df['passRecipientName']].index
    passes_df.drop(index_names, inplace=True)
    passes_df = passes_df.merge(match_players_df, on=['playerId', 'playerName'], how='left', validate='m:1')
    passes_df = passes_df.merge(match_players_df.rename({'playerId': 'passRecipientId', 'playerName':'passRecipientName'},
                                                        axis='columns'), on=['passRecipientId', 'passRecipientName'],
                                                        how='left', validate='m:1', suffixes=['', 'Receipt'])
    passes_df = passes_df[passes_df['playerPos'] != 'Sub']
    
    
    # getting team formation
    formation = match_data[venue]['formations'][0]['formationName']
    formation = '-'.join(formation)
    
    
    # getting player average locations
    location_formation = passes_df[['playerKitNumber', 'x', 'y']]
    average_locs_and_count = location_formation.groupby('playerKitNumber').agg({'x': ['mean'], 'y': ['mean', 'count']})
    average_locs_and_count.columns = ['x', 'y', 'count']
    
    
    # filtering progressive passes 
    passes_df = passes_df.loc[passes_df['EPV_difference'] > 0]

    
    # getting separate dataframe for selected columns 
    passes_formation = passes_df[['id', 'playerKitNumber', 'playerKitNumberReceipt']].copy()
    passes_formation['EPV'] = passes_df['EPV_difference']


    # getting dataframe for passes between players
    passes_between = passes_formation.groupby(['playerKitNumber', 'playerKitNumberReceipt']).agg({ 'id' : 'count', 'EPV' : 'sum'}).reset_index()
    passes_between.rename({'id': 'pass_count'}, axis='columns', inplace=True)
    passes_between = passes_between.merge(average_locs_and_count, left_on='playerKitNumberReceipt', right_index=True)
    passes_between = passes_between.merge(average_locs_and_count, left_on='playerKitNumber', right_index=True,
                                          suffixes=['', '_end'])
    
    
    # filtering passes
    pass_filter = int(passes_between['pass_count'].mean())
    passes_between = passes_between.loc[passes_between['pass_count'] > pass_filter*2]

    
    # calculating the line width 
    max_line_width = max_lw
    passes_between['width'] = passes_between.pass_count / passes_between.pass_count.max() * max_line_width
    passes_between = passes_between.reset_index(drop=True)
    
    
    # setting color to make the lines more transparent when fewer passes are made
    min_transparency = 0.3
    color = np.array(to_rgba('white'))
    color = np.tile(color, (len(passes_between), 1))
    c_transparency = passes_between.EPV / passes_between.EPV.max()
    c_transparency = (c_transparency * (1 - min_transparency)) + min_transparency
    color[:, 3] = c_transparency
    passes_between['alpha'] = color.tolist()
    
    
    
    # plotting
    pitch = Pitch(pitch_type='statsbomb', orientation='horizontal',
                  pitch_color=pitch_color, line_color='#c7d5cc', figsize=(16, 11),
                  constrained_layout=True, tight_layout=False)
    fig, ax = pitch.draw()
    
    average_locs_and_count['zorder'] = list(np.linspace(2,6,11, dtype='int'))
    pitch.lines(passes_between.x/100*120, 80-passes_between.y/100*80,
                passes_between.x_end/100*120, 80-passes_between.y_end/100*80, lw=passes_between.width,
                color=color, zorder=1, ax=ax)
    for index, row in average_locs_and_count.iterrows():
        pitch.scatter(row.x/100*120, 80-row.y/100*80, s=marker_size,
                      color=marker_color, edgecolors='black', linewidth=1, 
                      alpha=1, zorder=row.zorder, ax=ax)
    
    
    for index, row in average_locs_and_count.iterrows():
        pitch.annotate(row.name, xy=(row.x/100*120, 80-row.y/100*80), family='DejaVu Sans', c='white', 
                       va='center', ha='center', zorder=row.zorder, size=20, weight='bold', ax=ax)
    ax.set_title("{} Progressive Pass Network vs {}".format(team, opponent), size=15, y=0.97, color='#c7d5cc')
    fig.set_facecolor(pitch_color)
    #ax.text(2, 78, '{}'.format(formation), size=9, c='grey')
    #plt.savefig(f'visualisations\{team} Progressive Pass Network vs {opponent}.png', facecolor=fig.get_facecolor(), edgecolor='none')

    
    






def getTeamSuccessfulBoxPasses(events_df, teamId, team, pitch_color, cmap):
    """
    Parameters
    ----------
    events_df : DataFrame of all events.
    
    teamId : ID of the team, the passes of which are required.
    
    team : Name of the team, the passes of which are required.
    
    pitch_color : color of the pitch.
    
    cmap : color design of the pass lines. 
           You can select more cmaps here: 
               https://matplotlib.org/3.1.0/tutorials/colors/colormaps.html

    Returns
    -------
    Pitch Plot.

    """
    
    # Get Total Passes
    passes_df = events_df.loc[[row['displayName'] == 'Pass' for row in list(events_df['type'])]].reset_index(drop=True)
    
    # Get Team Passes
    team_passes = passes_df.loc[passes_df['teamId'] == teamId]
        
    # Extracting Box Passes from Total Passes
    box_passes = team_passes.copy()
    for i,pas in box_passes.iterrows():
        X = pas["x"]/100*120
        Xend = pas["endX"]/100*120
        Y = pas["y"]/100*80
        Yend = pas["endY"]/100*80
        if Xend >= 102 and Yend >= 18 and Yend <= 62:
            if X >=102 and Y >= 18 and Y <= 62:
                box_passes = box_passes.drop([i])
            else:
                pass
        else:
            box_passes = box_passes.drop([i])
            
    successful_box_passes = box_passes.copy()
    unsuccessful_box_passes = box_passes.copy()
    for i,pas in box_passes.iterrows():
        if pas['outcomeType']['value'] == 0:
            successful_box_passes = successful_box_passes.drop([i])
        else:
            unsuccessful_box_passes = unsuccessful_box_passes.drop([i])
        
    
    pitch = Pitch(pitch_type='statsbomb', orientation='vertical', pitch_color=pitch_color, line_color='#c7d5cc',
                  figsize=(16, 11), view='half', pad_top=2, tight_layout=True)
    fig, ax = pitch.draw()
    
    # Plot the completed passes
    pitch.lines(successful_box_passes.x/100*120, 80-successful_box_passes.y/100*80,
                successful_box_passes.endX/100*120, 80-successful_box_passes.endY/100*80,
                lw=5, opp_transparent=True, opp_comet=True, cmap=cmap,
                label='Successful Passes', ax=ax)
    
    pitch.scatter(successful_box_passes.x/100*120, 80-successful_box_passes.y/100*80,
                  edgecolors='white', c='white', s=50, zorder=2,
                  ax=ax)
    
    # Set the title
    fig.suptitle(f'Completed Box Passes - {team}', fontsize=15)
    
    # Set the subtitle
    ax.set_title('Data : Whoscored', fontsize=8, loc='right', fontstyle='italic', fontweight='bold')
    
    # set legend
    #ax.legend(facecolor='#22312b', edgecolor='None', fontsize=8, loc='lower center', handlelength=4)
    
    # Set the figure facecolor
    fig.set_facecolor(pitch_color) 








def getTeamTotalPasses(events_df, teamId, team, opponent, pitch_color):
    """
    

    Parameters
    ----------
    events_df : DataFrame of all events.
    
    teamId : ID of the team, the passes of which are required.
    
    team : Name of the team, the passes of which are required.
    
    opponent : Name of opponent team.
    
    pitch_color : color of the pitch.


    Returns
    -------
    Pitch Plot.
    """
    
    # Get Total Passes
    passes_df = events_df.loc[[row['displayName'] == 'Pass' for row in list(events_df['type'])]].reset_index(drop=True)
    
    # Get Team Passes
    team_passes = passes_df.loc[passes_df['teamId'] == teamId]
        
    successful_passes = team_passes.copy()
    unsuccessful_passes = team_passes.copy()
    for i,pas in team_passes.iterrows():
        if pas['outcomeType']['value'] == 0:
            successful_passes = successful_passes.drop([i])
        else:
            unsuccessful_passes = unsuccessful_passes.drop([i])
            
    # Setup the pitch
    pitch = Pitch(pitch_type='statsbomb', orientation='horizontal',
                  pitch_color=pitch_color, line_color='#c7d5cc', figsize=(16, 11),
                  constrained_layout=True, tight_layout=False)
    fig, ax = pitch.draw()
    
    # Plot the completed passes
    pitch.arrows(successful_passes.x/100*120, 80-successful_passes.y/100*80,
                 successful_passes.endX/100*120, 80-successful_passes.endY/100*80, width=1,
                 headwidth=10, headlength=10, color='#ad993c', ax=ax, label='Completed')
    
    # Plot the other passes
    pitch.arrows(unsuccessful_passes.x/100*120, 80-unsuccessful_passes.y/100*80,
                 unsuccessful_passes.endX/100*120, 80-unsuccessful_passes.endY/100*80, width=1,
                 headwidth=6, headlength=5, headaxislength=12, color='#ba4f45', ax=ax, label='Blocked')
    
    # setup the legend
    ax.legend(facecolor=pitch_color, handlelength=5, edgecolor='None', fontsize=8, loc='upper left', shadow=True)
    
    # Set the title
    fig.suptitle(f'{team} Passes vs {opponent}', fontsize=15)
    
    
    # Set the subtitle
    ax.set_title('Data : Whoscored', fontsize=8, loc='right', fontstyle='italic', fontweight='bold')
    
    
    # Set the figure facecolor
    
    fig.set_facecolor(pitch_color)
