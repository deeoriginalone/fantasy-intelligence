import pandas as pd

projections = pd.read_csv("data/master_player_projections.csv")
injuries = pd.read_csv("data/injury_risk_report.csv")
draft_board = pd.read_csv("data/draft_board.csv")

print("Projections:", projections.shape)
print("Injuries:", injuries.shape)
print("Draft Board:", draft_board.shape)

print(
    projections[
        ['Player','Team','Position','Projected_FPTS','Injury_Status']
    ].head()
)
