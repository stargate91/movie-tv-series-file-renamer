def transfer_metadata_to_api_to_get_episode(id_handled, api_client):
	episodes = []
	unknown = []

	for file_data in id_handled:
		file_path = file_data['file_path']
		file_type = file_data['file_type']
		series_details = file_data['series_details']
		series_id = file_data['series_details']['id']
		season = file_data['season']
		episode = file_data['episode']
		extras = file_data['extras']

		e_detail = api_client.get_from_tmdb_episode(series_id, season, episode)

		if series_details and e_detail:
			episodes.append({
				"file_path": file_data['file_path'],
				"file_type": file_data['file_type'],
				"series_details": series_details,
				"episode_details": e_detail, 
				"extras": extras
			})

		else:
			unknown.append(file_data)
			print(f"No episode found for {file_path}")

	return episodes, unknown