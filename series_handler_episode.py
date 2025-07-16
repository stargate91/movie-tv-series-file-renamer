def transfer_metadata_to_api_to_get_episode(id_handled, api_client):
	episodes = []
	unknown = []

	for file_data in id_handled:
		file_path = file_data['file_path']
		data = file_data['data']
		series_id = file_data['data']['id']
		season = file_data['season']
		episode = file_data['episode']
		extras = file_data['extras']

		e_detail = api_client.get_from_tmdb_episode(series_id, season, episode)

		if data and e_detail:
			episodes.append({
				"file_path": file_data['file_path'],
				"series_details": data,
				"episode_details": e_detail, 
				"extras": extras
			})

		else:
			unknown.append(file_data)
			print(f"No episode found for {file_path}")

	return episodes, unknown