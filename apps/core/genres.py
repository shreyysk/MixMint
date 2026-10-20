"""One genre list for uploads, edits and search filters.

Style genres describe the sound; regional genres describe the language or scene the track comes from
(Mangalore/Tulu/Kannada etc.). A track has one genre; "Other" is always last."""

STYLE_GENRES = [
    "Techno", "House", "Tech House", "Deep House", "Afro House", "Progressive", "Trance", "Psytrance",
    "Dubstep", "Drum & Bass", "Hardstyle", "EDM", "Hip-Hop", "Bollywood", "Bollywood Remix", "Tollywood",
    "Lo-fi",
]
REGIONAL_GENRES = [
    "Mangalore", "Tulu", "Kannada", "Konkani", "Tamil", "Telugu", "Malayalam", "Hindi", "Marathi",
    "Punjabi", "Bengali", "Gujarati", "Bhojpuri", "English",
]
GENRES = STYLE_GENRES + REGIONAL_GENRES + ["Other"]
GENRE_GROUPS = [("Style", STYLE_GENRES), ("Regional & language", REGIONAL_GENRES), ("More", ["Other"])]
