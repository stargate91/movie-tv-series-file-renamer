def get_ratings_from_omdb(api_client, imdb_id):
    omdb_data = api_client.get_from_omdb_by_imdb_id(imdb_id)

    imdb_rating = "Unknown IMDb Rating"
    rotten_rating = "Unknown Rotten Tomatoes Rating"
    metacritic_rating = "Unknown Metacritic Rating"

    for rating in omdb_data.get("Ratings", []):
        source = rating['Source']
        value = rating['Value']

        if source == "Internet Movie Database":
            try:
                imdb_rating = float(value.split("/")[0])
            except (ValueError, IndexError):
                imdb_rating = "Unknown IMDb Rating"
        elif source == "Rotten Tomatoes":
            try:
                rotten_rating = value.replace("%", "")
            except (ValueError, IndexError):
                rotten_rating = "Unknown Rotten Tomatoes Rating"
        elif source == "Metacritic":
            try:
                metacritic_rating = value.split("/")[0]
            except (ValueError, IndexError):
                metacritic_rating = "Unknown Metacritic Rating"

    return imdb_rating, rotten_rating, metacritic_rating

def enricher(standardized_files, api_client):
    enriched_files = []
    unexpected_episodes = []

    for file_data in standardized_files:
        file_type = file_data['file_type']
        tmdb_id = file_data['tmdb_id']

        if file_type == "movie":
            movie_data = api_client.get_from_tmdb_movie_detail(tmdb_id)
            imdb_id = movie_data.get('imdb_id', 'Unknown IMDb ID')
            genres_raw = movie_data.get('genres', 'Unknown Genres')
            genre_names = [genre["name"] for genre in genres_raw]
            genres = " ".join(genre_names)

            imdb_rating, rotten_rating, metacritic_rating = get_ratings_from_omdb(api_client, imdb_id)

            enriched_files.append({
                **file_data,
                "genres": genres,
                "imdb_rating": imdb_rating,
                "rotten_rating": rotten_rating,
                "metacritic_rating": metacritic_rating
            })

        if file_type == "episode":
            season = file_data['season_number']
            episode = file_data['episode_number']
            series_data = api_client.get_from_tmdb_tv_detail(tmdb_id)
            status = series_data.get('status')
            last_air_date = series_data.get('last_air_date', 'Ongoing')
            if last_air_date != "Ongoing":
                last_air_year = last_air_date.split('-')[0]
            else:
                last_air_year = "Ongoing"
            genres_raw = series_data.get('genres', 'Unknown Genres')
            genre_names = [genre["name"] for genre in genres_raw]
            genres = " ".join(genre_names)

            series_exeternal_data = api_client.get_from_tmdb_tv_external(tmdb_id)
            imdb_id = series_exeternal_data.get('imdb_id', 'Unknown IMDb ID')

            episode_data = api_client.get_from_tmdb_episode(tmdb_id, season, episode)

            if episode_data:
                episode_title = episode_data.get('name', 'Unknown Episode Title')
                season_number = episode_data.get('season_number', 'Unknown Season')
                episode_number = episode_data.get('episode_number', 'Episode Number')
                air_date = episode_data.get('air_date', 'Unknown Air Date')
                air_year = air_date.split('-')[0]
            else:
                unexpected_episodes.append(file_data)
                print(f"[WARNING] No episode found for {file_data['file_path']}")

            imdb_rating, rotten_rating, metacritic_rating = get_ratings_from_omdb(api_client, imdb_id)

            enriched_files.append({
                **file_data,
                "genres": genres,
                "last_air_date": last_air_date,
                "last_air_year": last_air_year,
                "episode_title": episode_title,
                "season_number": season_number,
                "episode_number": episode_number,
                "air_date": air_date,
                "air_year": air_year,
                "imdb_rating": imdb_rating,
                "rotten_rating": rotten_rating,
                "metacritic_rating": metacritic_rating
            })

    return enriched_files, unexpected_episodes
