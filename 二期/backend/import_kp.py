#!/usr/bin/env python3
import json, sys, os, uuid
sys.path.insert(0, '/opt/zhuguang/backend')
os.environ['ENV_FILE'] = '/opt/zhuguang/config/.env'

from database.connection import engine
from database.entities import KnowledgePoint
from sqlalchemy.orm import Session
from sqlalchemy import text

with Session(engine) as session:
    count = session.execute(text('SELECT COUNT(*) FROM knowledge_points')).scalar()
    if count > 0:
        print(f'already has {count} records, skip')
        sys.exit(0)

with open('/opt/zhuguang/backend/data/knowledge_points.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

book_map = {
    '\u9a6c\u514b\u601d\u4e3b\u4e49\u57fa\u672c\u539f\u7406': 'marxism',
    '\u601d\u60f3\u9053\u5fb7\u4e0e\u6cd5\u6cbb': 'morality',
    '\u4e60\u8fd1\u5e73\u65b0\u65f6\u4ee3\u4e2d\u56fd\u7279\u8272\u793e\u4f1a\u4e3b\u4e49\u601d\u60f3\u6982\u8bba': 'xi_thought',
}

cat_prefix = {'marxism': 'MY', 'morality': 'SD', 'xi_thought': 'XG'}

with Session(engine) as session:
    for i, kp in enumerate(data):
        book = kp.get('book_name', '')
        cat = book_map.get(book, 'other')
        prefix = cat_prefix.get(cat, 'OT')
        code = f'{prefix}-{i+1:04d}'

        keywords_list = kp.get('typical_keywords', [])
        if isinstance(keywords_list, list):
            keywords_str = ','.join(keywords_list)
        else:
            keywords_str = str(keywords_list)

        desc = kp.get('theory_description', '')

        point = KnowledgePoint(
            id=str(uuid.uuid4()),
            code=code,
            name=kp.get('name', ''),
            category=cat,
            chapter=kp.get('chapter', ''),
            description=desc,
            keywords=keywords_str[:500],
            is_active=True
        )
        session.add(point)
    session.commit()
    print(f'imported {len(data)} knowledge points')
