"""List feedback for a local operator without changing it.

Run from app/backend: ../../.venv/bin/python -m scripts.list_feedback
"""
import argparse
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import Feedback, engine


def main():
    parser=argparse.ArgumentParser(description='List private demo feedback as JSON lines.')
    parser.add_argument('--status',choices=('open','resolved','all'),default='open')
    parser.add_argument('--limit',type=int,default=100)
    args=parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error('--limit must be between 1 and 1000')
    query=select(Feedback).order_by(Feedback.created_at.desc(),Feedback.id.desc()).limit(args.limit)
    if args.status!='all': query=query.where(Feedback.status==args.status)
    with Session(engine) as session:
        for report in session.scalars(query):
            print(json.dumps({'id':report.id,'lesson_id':report.lesson_id,'category':report.category,
                              'status':report.status,'created_at':report.created_at.isoformat()+'Z',
                              'message':report.message,'clarity_rating':report.clarity_rating,'lesson_title':report.lesson_title,'exercise_id':report.exercise_id,'exercise_prompt':report.exercise_prompt},ensure_ascii=False))

if __name__=='__main__': main()
