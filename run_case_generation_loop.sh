#!/bin/bash
# 循环运行案例生成脚本，直到所有案例都生成完毕

cd "D:\AI-Empowered IPTC Website\一期"

echo "开始循环生成案例..."
echo "当前时间: $(date)"

for i in {1..30}; do
    echo ""
    echo "=========================================="
    echo "第 $i 轮开始"
    echo "=========================================="

    # 运行案例生成脚本
    python backend/scripts/batch_match_cases.py

    echo "第 $i 轮完成"

    # 检查当前进度
    python -c "
import sys
sys.path.insert(0, 'backend')
from database.connection import create_session
from database.entities import IPTCCase, IPTCKnowledgePointStats, IPTCMessageKnowledgeRelation
from sqlalchemy import func

with create_session() as db:
    case_count = db.query(func.count(IPTCCase.id)).scalar()
    generated_ids = db.query(IPTCKnowledgePointStats.knowledge_point_id).filter(
        IPTCKnowledgePointStats.case_generated == 1
    ).all()
    generated_ids = [row[0] for row in generated_ids]
    pending_count = db.query(
        IPTCMessageKnowledgeRelation.knowledge_point_id
    ).filter(
        ~IPTCMessageKnowledgeRelation.knowledge_point_id.in_(generated_ids) if generated_ids else True
    ).group_by(
        IPTCMessageKnowledgeRelation.knowledge_point_id
    ).having(
        func.count(IPTCMessageKnowledgeRelation.message_id) >= 4
    ).count()
    print(f'当前案例数: {case_count}, 待生成: {pending_count}')
    if pending_count == 0:
        print('所有案例已生成完毕！')
        exit(0)
"

    # 检查是否完成
    if [ $? -eq 0 ]; then
        echo "所有案例生成完成！"
        break
    fi

    # 休息5秒
    echo "休息5秒..."
    sleep 5
done

echo ""
echo "=========================================="
echo "循环生成结束"
echo "当前时间: $(date)"
echo "=========================================="
