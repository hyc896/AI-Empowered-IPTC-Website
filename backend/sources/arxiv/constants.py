# -*- coding: utf-8 -*-

"""
arXiv分类常量（官方完整列表 - 156个分类）
数据来源：https://arxiv.org/category_taxonomy
"""

VALID_CATEGORIES = [
    # 计算机科学 (Computer Science) - 40个
    'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV',
    'cs.CY', 'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL',
    'cs.GL', 'cs.GR', 'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO',
    'cs.MA', 'cs.MM', 'cs.MS', 'cs.NA', 'cs.NE', 'cs.NI', 'cs.OH', 'cs.OS',
    'cs.PF', 'cs.PL', 'cs.RO', 'cs.SC', 'cs.SD', 'cs.SE', 'cs.SI', 'cs.SY',

    # 经济学 (Economics) - 3个
    'econ.EM', 'econ.GN', 'econ.TH',

    # 电气工程与系统科学 (Electrical Engineering and Systems Science) - 4个
    'eess.AS', 'eess.IV', 'eess.SP', 'eess.SY',

    # 数学 (Mathematics) - 32个
    'math.AC', 'math.AG', 'math.AP', 'math.AT', 'math.CA', 'math.CO', 'math.CT',
    'math.CV', 'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN', 'math.GR',
    'math.GT', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MG', 'math.MP',
    'math.NA', 'math.NT', 'math.OA', 'math.OC', 'math.PR', 'math.QA', 'math.RA',
    'math.RT', 'math.SG', 'math.SP', 'math.ST',

    # 天体物理学 (Astrophysics) - 6个
    'astro-ph.CO', 'astro-ph.EP', 'astro-ph.GA', 'astro-ph.HE', 'astro-ph.IM', 'astro-ph.SR',

    # 凝聚态物理 (Condensed Matter) - 9个
    'cond-mat.dis-nn', 'cond-mat.mes-hall', 'cond-mat.mtrl-sci', 'cond-mat.other',
    'cond-mat.quant-gas', 'cond-mat.soft', 'cond-mat.stat-mech', 'cond-mat.str-el', 'cond-mat.supr-con',

    # 广义相对论和量子宇宙学 (General Relativity and Quantum Cosmology) - 1个
    'gr-qc',

    # 高能物理 (High Energy Physics) - 4个
    'hep-ex', 'hep-lat', 'hep-ph', 'hep-th',

    # 数学物理 (Mathematical Physics) - 1个
    'math-ph',

    # 非线性科学 (Nonlinear Sciences) - 5个
    'nlin.AO', 'nlin.CD', 'nlin.CG', 'nlin.PS', 'nlin.SI',

    # 核物理 (Nuclear) - 2个
    'nucl-ex', 'nucl-th',

    # 物理学 (Physics) - 22个
    'physics.acc-ph', 'physics.ao-ph', 'physics.app-ph', 'physics.atm-clus', 'physics.atom-ph',
    'physics.bio-ph', 'physics.chem-ph', 'physics.class-ph', 'physics.comp-ph', 'physics.data-an',
    'physics.ed-ph', 'physics.flu-dyn', 'physics.gen-ph', 'physics.geo-ph', 'physics.hist-ph',
    'physics.ins-det', 'physics.med-ph', 'physics.optics', 'physics.plasm-ph', 'physics.pop-ph',
    'physics.soc-ph', 'physics.space-ph',

    # 量子物理 (Quantum Physics) - 1个
    'quant-ph',

    # 定量生物学 (Quantitative Biology) - 10个
    'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC',
    'q-bio.OT', 'q-bio.PE', 'q-bio.QM', 'q-bio.SC', 'q-bio.TO',

    # 定量金融 (Quantitative Finance) - 9个
    'q-fin.CP', 'q-fin.EC', 'q-fin.GN', 'q-fin.MF', 'q-fin.PM',
    'q-fin.PR', 'q-fin.RM', 'q-fin.ST', 'q-fin.TR',

    # 统计学 (Statistics) - 6个
    'stat.AP', 'stat.CO', 'stat.ME', 'stat.ML', 'stat.OT', 'stat.TH',
]

CATEGORY_NAMES = {
    # 计算机科学 (Computer Science)
    'cs.AI': '人工智能',
    'cs.AR': '硬件架构',
    'cs.CC': '计算复杂度',
    'cs.CE': '计算工程、金融和科学',
    'cs.CG': '计算几何',
    'cs.CL': '计算和语言',
    'cs.CR': '密码学与安全',
    'cs.CV': '计算机视觉和模式识别',
    'cs.CY': '计算机与社会',
    'cs.DB': '数据库',
    'cs.DC': '分布式、并行和集群计算',
    'cs.DL': '数字图书馆',
    'cs.DM': '离散数学',
    'cs.DS': '数据结构和算法',
    'cs.ET': '新兴技术',
    'cs.FL': '形式语言与自动机理论',
    'cs.GL': '通用文献',
    'cs.GR': '图形学',
    'cs.GT': '计算机科学与博弈论',
    'cs.HC': '人机交互',
    'cs.IR': '信息检索',
    'cs.IT': '信息论',
    'cs.LG': '机器学习',
    'cs.LO': '计算机科学中的逻辑',
    'cs.MA': '多智能体系统',
    'cs.MM': '多媒体',
    'cs.MS': '数学软件',
    'cs.NA': '数值分析',
    'cs.NE': '神经与进化计算',
    'cs.NI': '网络和互联网架构',
    'cs.OH': '其他计算机科学',
    'cs.OS': '操作系统',
    'cs.PF': '性能',
    'cs.PL': '编程语言',
    'cs.RO': '机器人学',
    'cs.SC': '符号计算',
    'cs.SD': '声音',
    'cs.SE': '软件工程',
    'cs.SI': '社交和信息网络',
    'cs.SY': '系统与控制',

    # 经济学 (Economics)
    'econ.EM': '计量经济学',
    'econ.GN': '普通经济学',
    'econ.TH': '理论经济学',

    # 电气工程与系统科学 (Electrical Engineering and Systems Science)
    'eess.AS': '音频和语音处理',
    'eess.IV': '图像和视频处理',
    'eess.SP': '信号处理',
    'eess.SY': '系统与控制',

    # 数学 (Mathematics)
    'math.AC': '交换代数',
    'math.AG': '代数几何',
    'math.AP': '分析学中的偏微分方程',
    'math.AT': '代数拓扑',
    'math.CA': '经典分析和ODE',
    'math.CO': '组合数学',
    'math.CT': '范畴论',
    'math.CV': '复变量',
    'math.DG': '微分几何',
    'math.DS': '动力系统',
    'math.FA': '泛函分析',
    'math.GM': '普通数学',
    'math.GN': '一般拓扑',
    'math.GR': '群论',
    'math.GT': '几何拓扑',
    'math.HO': '数学史与综述',
    'math.IT': '信息论',
    'math.KT': 'K理论与同调代数',
    'math.LO': '逻辑学',
    'math.MG': '度量几何',
    'math.MP': '数学物理',
    'math.NA': '数值分析',
    'math.NT': '数论',
    'math.OA': '算子代数',
    'math.OC': '优化与控制',
    'math.PR': '概率',
    'math.QA': '量子代数',
    'math.RA': '环和代数',
    'math.RT': '表示论',
    'math.SG': '辛几何',
    'math.SP': '谱理论',
    'math.ST': '统计理论',

    # 天体物理学 (Astrophysics)
    'astro-ph.CO': '宇宙学和非星系天体物理学',
    'astro-ph.EP': '地球和行星天体物理学',
    'astro-ph.GA': '星系天体物理学',
    'astro-ph.HE': '高能天体物理现象',
    'astro-ph.IM': '天体物理学仪器和方法',
    'astro-ph.SR': '太阳和恒星天体物理学',

    # 凝聚态物理 (Condensed Matter)
    'cond-mat.dis-nn': '无序系统和神经网络',
    'cond-mat.mes-hall': '介观系统和量子霍尔效应',
    'cond-mat.mtrl-sci': '材料科学',
    'cond-mat.other': '其他凝聚态物质',
    'cond-mat.quant-gas': '量子气体',
    'cond-mat.soft': '软凝聚态物质',
    'cond-mat.stat-mech': '统计力学',
    'cond-mat.str-el': '强关联电子',
    'cond-mat.supr-con': '超导性',

    # 广义相对论和量子宇宙学 (General Relativity and Quantum Cosmology)
    'gr-qc': '广义相对论和量子宇宙学',

    # 高能物理 (High Energy Physics)
    'hep-ex': '高能物理-实验',
    'hep-lat': '高能物理-格点',
    'hep-ph': '高能物理-唯象学',
    'hep-th': '高能物理-理论',

    # 数学物理 (Mathematical Physics)
    'math-ph': '数学物理',

    # 非线性科学 (Nonlinear Sciences)
    'nlin.AO': '适应和自组织系统',
    'nlin.CD': '混沌动力学',
    'nlin.CG': '细胞自动机和格子气体',
    'nlin.PS': '模式形成和孤子',
    'nlin.SI': '精确可解可积系统',

    # 核物理 (Nuclear)
    'nucl-ex': '核实验',
    'nucl-th': '核理论',

    # 物理学 (Physics)
    'physics.acc-ph': '加速器物理',
    'physics.ao-ph': '大气和海洋物理',
    'physics.app-ph': '应用物理',
    'physics.atm-clus': '原子和分子团簇',
    'physics.atom-ph': '原子物理',
    'physics.bio-ph': '生物物理',
    'physics.chem-ph': '化学物理',
    'physics.class-ph': '经典物理',
    'physics.comp-ph': '计算物理',
    'physics.data-an': '数据分析、统计和概率',
    'physics.ed-ph': '物理教育',
    'physics.flu-dyn': '流体动力学',
    'physics.gen-ph': '普通物理',
    'physics.geo-ph': '地球物理学',
    'physics.hist-ph': '物理史与哲学',
    'physics.ins-det': '仪器和探测器',
    'physics.med-ph': '医学物理',
    'physics.optics': '光学',
    'physics.plasm-ph': '等离子体物理',
    'physics.pop-ph': '大众物理',
    'physics.soc-ph': '社会物理学',
    'physics.space-ph': '空间物理',

    # 量子物理 (Quantum Physics)
    'quant-ph': '量子物理',

    # 定量生物学 (Quantitative Biology)
    'q-bio.BM': '生物分子',
    'q-bio.CB': '细胞行为',
    'q-bio.GN': '基因组学',
    'q-bio.MN': '分子网络',
    'q-bio.NC': '神经元和认知',
    'q-bio.OT': '其他定量生物学',
    'q-bio.PE': '种群和进化',
    'q-bio.QM': '定量方法',
    'q-bio.SC': '亚细胞过程',
    'q-bio.TO': '组织和器官',

    # 定量金融 (Quantitative Finance)
    'q-fin.CP': '计算金融',
    'q-fin.EC': '经济学',
    'q-fin.GN': '通用金融',
    'q-fin.MF': '数学金融',
    'q-fin.PM': '投资组合管理',
    'q-fin.PR': '定价与风险管理',
    'q-fin.RM': '风险管理',
    'q-fin.ST': '统计金融',
    'q-fin.TR': '交易与市场微观结构',

    # 统计学 (Statistics)
    'stat.AP': '应用程序',
    'stat.CO': '计算',
    'stat.ME': '方法论',
    'stat.ML': '机器学习',
    'stat.OT': '其他统计数据',
    'stat.TH': '统计理论',
}

CATEGORY_GROUPS = {
    '计算机科学': [
        'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV',
        'cs.CY', 'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL',
        'cs.GL', 'cs.GR', 'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO',
        'cs.MA', 'cs.MM', 'cs.MS', 'cs.NA', 'cs.NE', 'cs.NI', 'cs.OH', 'cs.OS',
        'cs.PF', 'cs.PL', 'cs.RO', 'cs.SC', 'cs.SD', 'cs.SE', 'cs.SI', 'cs.SY',
    ],
    '经济学': ['econ.EM', 'econ.GN', 'econ.TH'],
    '电气工程与系统科学': ['eess.AS', 'eess.IV', 'eess.SP', 'eess.SY'],
    '数学': [
        'math.AC', 'math.AG', 'math.AP', 'math.AT', 'math.CA', 'math.CO', 'math.CT',
        'math.CV', 'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN', 'math.GR',
        'math.GT', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MG', 'math.MP',
        'math.NA', 'math.NT', 'math.OA', 'math.OC', 'math.PR', 'math.QA', 'math.RA',
        'math.RT', 'math.SG', 'math.SP', 'math.ST',
    ],
    '天体物理学': [
        'astro-ph.CO', 'astro-ph.EP', 'astro-ph.GA', 'astro-ph.HE', 'astro-ph.IM', 'astro-ph.SR',
    ],
    '凝聚态物理': [
        'cond-mat.dis-nn', 'cond-mat.mes-hall', 'cond-mat.mtrl-sci', 'cond-mat.other',
        'cond-mat.quant-gas', 'cond-mat.soft', 'cond-mat.stat-mech', 'cond-mat.str-el', 'cond-mat.supr-con',
    ],
    '广义相对论和量子宇宙学': ['gr-qc'],
    '高能物理': ['hep-ex', 'hep-lat', 'hep-ph', 'hep-th'],
    '数学物理': ['math-ph'],
    '非线性科学': ['nlin.AO', 'nlin.CD', 'nlin.CG', 'nlin.PS', 'nlin.SI'],
    '核物理': ['nucl-ex', 'nucl-th'],
    '物理学': [
        'physics.acc-ph', 'physics.ao-ph', 'physics.app-ph', 'physics.atm-clus', 'physics.atom-ph',
        'physics.bio-ph', 'physics.chem-ph', 'physics.class-ph', 'physics.comp-ph', 'physics.data-an',
        'physics.ed-ph', 'physics.flu-dyn', 'physics.gen-ph', 'physics.geo-ph', 'physics.hist-ph',
        'physics.ins-det', 'physics.med-ph', 'physics.optics', 'physics.plasm-ph', 'physics.pop-ph',
        'physics.soc-ph', 'physics.space-ph',
    ],
    '量子物理': ['quant-ph'],
    '定量生物学': [
        'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC',
        'q-bio.OT', 'q-bio.PE', 'q-bio.QM', 'q-bio.SC', 'q-bio.TO',
    ],
    '定量金融': [
        'q-fin.CP', 'q-fin.EC', 'q-fin.GN', 'q-fin.MF', 'q-fin.PM',
        'q-fin.PR', 'q-fin.RM', 'q-fin.ST', 'q-fin.TR',
    ],
    '统计学': ['stat.AP', 'stat.CO', 'stat.ME', 'stat.ML', 'stat.OT', 'stat.TH'],
}
