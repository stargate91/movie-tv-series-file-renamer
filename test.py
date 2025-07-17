from guessit import guessit

filename = "Raiders.Of.The.Lost.Ark.1981.1080p.BluRay.DTS.x264.HuN-TRiNiTY\i1.1080p-trinity.mkv"
result = guessit(filename)

for key, value in result.items():
    print(f"{key}: {value}")
