def extract_episode_metadata(episodes, api_client):
	known = []
	unknown = []

	for file_data in episodes:
		series_details = file_data['series_details']
		series_id = series_details['id']
		season = file_data['season']
		episode = file_data['episode']

		e_detail = api_client.get_from_tmdb_episode(series_id, season, episode)

		if e_detail:
			known.append({
				"file_path": file_data['file_path'],
				"file_type": file_data['file_type'],
				"series_details": series_details,
				"episode_details": e_detail, 
				"extras": file_data['extras']
			})

		else:
			unknown.append(file_data)
			print(f"No episode found for {file_data['file_path']}")

	return known, unknown