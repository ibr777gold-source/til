"""Inspect or fulfill a pending learner account deletion request.

Usage: python -m scripts.fulfill_deletion USER_ID [--execute]
The default is read-only. --execute permanently deletes eligible account data.
"""
import argparse
import json
from sqlalchemy.orm import Session
from app.main import engine
from app.deletion import DeletionBlocked, deletion_plan, fulfill_deletion

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('user_id',type=int)
parser.add_argument('--execute',action='store_true',help='permanently fulfill the pending request')
args=parser.parse_args()
try:
    with Session(engine) as session:
        if args.execute:
            result=fulfill_deletion(session,args.user_id); session.commit()
            print(json.dumps({'status':'deleted',**result},sort_keys=True))
        else:
            _,counts=deletion_plan(session,args.user_id)
            print(json.dumps({'status':'dry_run','counts':counts},sort_keys=True))
except DeletionBlocked as error:
    raise SystemExit(str(error))
