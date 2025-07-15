from guessit import guessit

filename = "Hitch.2005.1080p.Bluray.Remux.MPEG2.TrueHD.5.1.HUN-KuNgZi.mkv"
result = guessit(filename)

for key, value in result.items():
    print(f"{key}: {value}")
