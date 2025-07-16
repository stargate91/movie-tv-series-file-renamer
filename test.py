from guessit import guessit

filename = "50.First.Dates.2004.1080p.RETAiL.BluRay.Remux.MPEG-2.TrueHD.5.1.HuN-Essence"
result = guessit(filename)

for key, value in result.items():
    print(f"{key}: {value}")
