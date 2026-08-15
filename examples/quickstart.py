"""Quick-start example for the Whoscored event-data SDK."""

from __future__ import annotations

from whoscored import WhoscoredClient

# --- Single match ---------------------------------------------------------
with WhoscoredClient() as client:
    match = client.get_match(1650630)  # numeric id or full URL

print(f"{match.home.name} {match.score} {match.away.name} "
      f"({match.league} {match.season})")

events = match.events
print(events.head())

# Add the Expected Possession Value column (successful passes only)
events_with_epv = match.add_epv()
print(events_with_epv["EPV"].describe())

# Match-level summary frame
print(match.matches_df)

# --- Several matches ------------------------------------------------------
# First obtain fixtures. The fixture listing page is Cloudflare-protected and
# needs the browser backend; or supply match URLs directly:
urls = [
    "https://www.whoscored.com/Matches/1650630/Live/Spain-LaLiga-2022-2023-Barcelona-Rayo-Vallecano",
    "https://www.whoscored.com/Matches/1650634/Live/Spain-LaLiga-2022-2023-Osasuna-Sevilla",
]
with WhoscoredClient() as client:
    matches = client.get_matches(urls)

combined = __import__("pandas").concat([m.events for m in matches], ignore_index=True)
print(combined.shape)

# --- Helpers ---------------------------------------------------------------
from whoscored import save_dataframe, load_dataframe

save_dataframe(events, "data/events_1650630.csv")
restored = load_dataframe("data/events_1650630.csv")
print(restored.shape)
