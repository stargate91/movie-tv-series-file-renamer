from movie_handlers import handle_movies_with_no_match, handle_movies_with_multiple_matches
from series_id_handlers import handle_episodes_with_no_match, handle_episodes_with_multiple_matches

def dispatcher(collected_results):

    movies_with_one_match = []
    movies_with_multiple_matches = []
    movies_with_no_match = []

    episodes_with_one_match = []
    episodes_with_multiple_matches = []
    episodes_with_no_match = []

    for file_data in collected_results:
        file_type = file_data.get('file_type')
        status = file_data.get('status')

        if file_type == "movie" and status == "one_match":
            movies_with_one_match.append(file_data)

        elif file_type == "movie" and status == "no_match":
            movies_with_no_match.append(file_data)

        elif file_type == "movie" and status == "multiple_matches":
            movies_with_multiple_matches.append(file_data)

        elif file_type == "episode" and status == "one_match":
            episodes_with_one_match.append(file_data)

        elif file_type == "episode" and status == "no_match":
            episodes_with_no_match.append(file_data)

        elif file_type == "episode" and status == "multiple_matches":
            episodes_with_multiple_matches.append(file_data)

    return (movies_with_one_match, movies_with_multiple_matches, movies_with_no_match, 
            episodes_with_one_match, episodes_with_multiple_matches, episodes_with_no_match)


def get_handler(collected_results, api_client, interactive):
    (
        movies_with_one_match,
        movies_with_multiple_matches,
        movies_with_no_match,
        episodes_with_one_match,
        episodes_with_multiple_matches,
        episodes_with_no_match
    ) = dispatcher(collected_results)

    handled_results = []
    skipped_results = []
    unprocessed_results = []

    handled_results += movies_with_one_match + episodes_with_one_match

    if interactive:
        h1, s1, u1 = handle_movies_with_no_match(movies_with_no_match, api_client)
        h2, s2, u2 = handle_movies_with_multiple_matches(movies_with_multiple_matches, api_client)
        h3, s3, u3 = handle_episodes_with_no_match(episodes_with_no_match, api_client)
        h4, s4, u4 = handle_episodes_with_multiple_matches(episodes_with_multiple_matches, api_client)

        handled_results += h1 + h2 + h3 + h4
        skipped_results += s1 + s2 + s3 + s4
        unprocessed_results += u1 + u2 + u3 + u4

    else:
        unprocessed_results += (
            movies_with_multiple_matches +
            movies_with_no_match +
            episodes_with_multiple_matches +
            episodes_with_no_match
        )

    return handled_results, skipped_results, unprocessed_results
