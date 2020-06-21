import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine("postgres://agoorupexafgjs:dc6ad14bb820be1db139d5c4ab49ef94f3704528342f5c49f478aa00ae4b3fca@ec2-50-17-90-177.compute-1.amazonaws.com:5432/daef7bbdn0jja1")
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    next(reader)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn":isbn, "title":title, "author":author, "year":year})
        print(title)
    db.commit()

if __name__ == "__main__":
    main()
