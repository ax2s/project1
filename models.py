import requests

def goodreads(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "f6akAxaefyRZt8MvKHLsA", "isbns": isbn})
    data = res.json()
    avg_rating = data['books'][0]['average_rating']
    n_ratings = data['books'][0]['work_ratings_count']
    gr_ratings = {'avg_rating': avg_rating, 'n_ratings': n_ratings}
    return gr_ratings
