"""Original bilingual academic schematics; no data or runtime claims are implied.

Layout brief follows Nature Figure's claim-first schematic design guidance.
English and Chinese labels are kept together to prevent semantic drift.
"""
from pathlib import Path
from html import escape
import json

ROOT = Path(__file__).resolve().parents[1]
BG, INK, MUTED, LINE = '#ffffff', '#233345', '#607181', '#cbd5dc'
TEAL, BLUE, AMBER = '#167d8d', '#536ca0', '#ae662c'
PALE, LILAC, SAND = '#eaf5f4', '#eff0f8', '#faf2e6'
LANG = 0
LABELS = {}


def txt(x, y, en, cn=None, size=23, color=INK, weight=400, anchor='start'):
    if cn is None:
        cn = en
    LABELS[en] = cn
    value = (en, cn)[LANG]
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>'


def box(x,y,w,h,fill=BG,stroke=LINE,r=7):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'


def line(d,color=TEAL,dash=False,arrow=True):
    style = ' stroke-dasharray="6 5"' if dash else ''
    tip = f' marker-end="url(#{color[1:]})"' if arrow else ''
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"{style}{tip}/>'


def circle(x,y,r,fill=PALE,stroke=TEAL):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>'


def document(x,y,color=TEAL):
    return box(x,y,38,48,BG,color,3)+line(f'M {x+9} {y+13} h 20 M {x+9} {y+23} h 20 M {x+9} {y+33} h 14',color,arrow=False)


def target(x,y):
    return circle(x,y,26,BG,TEAL)+circle(x,y,15,BG,TEAL)+circle(x,y,4,TEAL,TEAL)


def heading(letter,en,cn,sub_en,sub_cn):
    return txt(32,45,letter,size=25,weight=700)+txt(66,45,en,cn,27,weight=600)+txt(66,79,sub_en,sub_cn,18,MUTED)


def node(x,y,w,num,en,cn,sub_en,sub_cn,color=TEAL,fill=PALE):
    c=box(x,y,w,112,fill,color)
    c+=txt(x+18,y+27,num,size=16,color=color,weight=700)
    c+=txt(x+18,y+58,en,cn,24,weight=600)
    c+=txt(x+18,y+88,sub_en,sub_cn,17,MUTED)
    return c


def save(name,w,h,title,cn_title,body):
    markers=''.join(f'<marker id="{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>' for color in (TEAL,BLUE,AMBER,MUTED))
    title=(title,cn_title)[LANG]
    desc=('Conceptual workflow instructions; not experimental data or a recorded execution.','流程规则示意，不代表实验数据或真实执行记录。')[LANG]
    font='Arial, Helvetica, sans-serif' if LANG==0 else 'Microsoft YaHei, Noto Sans CJK SC, PingFang SC, sans-serif'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{desc}</desc><defs>{markers}</defs><rect width="{w}" height="{h}" fill="{BG}"/><g font-family="{font}">{body}</g></svg>\n'
    p=ROOT/'assets'/name
    if LANG:p=p.with_stem(p.stem+'-cn')
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(svg,encoding='utf-8')


def hero():
    c=line('M 44 55 H 128',TEAL,arrow=False)
    c+=txt(145,61,'RESEARCH & DEVELOPMENT','科研与开发',16,TEAL,600)
    c+=txt(44,136,'conduct-best-skills',size=53,weight=700)
    c+=txt(44,189,'Turn intent into evidence.','让目标落到成果与证据。',29,MUTED)
    c+=txt(44,260,'Understand the goal.','理解真正的目标。',21)
    c+=txt(44,294,'Coordinate the work.','协调合适的能力。',21)
    c+=txt(44,328,'Verify the outcome.','验证实际的成果。',21)
    # A compact method schematic, not a decorative neural network.
    c+=target(760,214)
    c+=txt(760,269,'Intent','目标',18,TEAL,600,'middle')
    c+=line('M 788 214 H 850')
    c+=circle(900,214,48,PALE,TEAL)+txt(900,208,'Conduct','总控',22,TEAL,600,'middle')+txt(900,234,'select + align','选择与对齐',14,MUTED,400,'middle')
    c+=line('M 900 166 V 105 H 1020',BLUE)+line('M 948 214 H 1020',TEAL)+line('M 900 262 V 323 H 1020',AMBER)
    for y,en,cn,color in [(75,'Skills','技能',BLUE),(184,'Tools','工具',TEAL),(293,'Agents*','代理*',AMBER)]:
        c+=box(1020,y,128,60,BG,color)+txt(1084,y+37,en,cn,21,color,600,'middle')
    c+=txt(760,386,'* When useful, supported and authorized','* 仅在有收益、环境支持且获准时',15,MUTED)
    save('branding/hero.svg',1200,430,'conduct-best-skills: from intent to evidence','conduct-best-skills：从目标到证据',c)


def workflow():
    c=heading('a','From intent to verified delivery','从目标理解到成果验证','Seven stages, with explicit decision and recovery paths','七个阶段，明确决策边界与恢复路径')
    first=[('01','Context','上下文','Sources + validity','来源与有效性'),('02','Goals','目标','Scope + acceptance','范围与验收'),('03','Plan','规划','Discover + match','发现与匹配')]
    for x,labels in zip([48,378,708],first):c+=node(x,119,276,*labels)
    c+=line('M 324 175 H 378')+line('M 654 175 H 708')
    c+=line('M 984 175 H 1020 V 355 H 984')
    c+=node(708,300,276,'04','Execute','执行','Dependencies + recovery','依赖与恢复')
    c+=node(378,300,276,'05','Verify','验证','Version + actual evidence','版本与实际证据')
    c+=node(48,300,276,'07','Deliver','交付','Status + remaining gaps','状态与剩余缺口')
    c+=line('M 708 355 H 654')+line('M 378 355 H 324')+txt(351,334,'pass','通过',15,TEAL,anchor='middle')
    c+=node(378,478,276,'06','Refine','修正','Root cause + targeted repair','根因与定向修复',AMBER,SAND)
    c+=line('M 516 412 V 478',AMBER)+txt(533,452,'gap','缺口',16,AMBER)
    c+=line('M 654 535 H 846 V 412',AMBER,dash=True)+txt(735,568,'repair, then reverify','修复后重新验证',16,AMBER)
    c+=line('M 378 535 H 186 V 412',AMBER,dash=True)+txt(48,568,'No feasible path / limit reached','无可行路线 / 达到限制',15,AMBER)
    c+=box(48,643,936,126,'#f7f9fa',LINE)
    c+=txt(70,675,'Decision boundary','决策边界',20,weight=600)
    c+=txt(70,706,'Material goal changes or missing authority: ask; only affected work waits.','目标实质变化或授权缺失：询问用户，仅受影响工作等待。',18)
    c+=txt(70,740,'Revisit by cause: sources → 01 · goals → 02 · capabilities → 03 · check method → 05','按原因回退：资料 → 01 · 目标 → 02 · 能力 → 03 · 验证方法 → 05',16,MUTED)
    save('diagrams/workflow.svg',1050,800,'Seven-stage workflow with bounded refinement','七阶段工作流与有限修正',c)


def comparison():
    c=heading('b','Make coordination explicit','让协调过程清楚可见','An organizational comparison; no measured performance claim','比较组织机制，不宣称经过测量的性能提升')
    for x in [40,550]:c+=box(x,115,460,390,BG,LINE)
    c+=txt(65,155,'Without a shared workflow','缺少共同工作流程',24,weight=600)
    c+=txt(575,155,'With a shared task contract','围绕共同任务约定',24,TEAL,600)
    for y,en,cn in [(205,'Which context matters?','需要哪些上下文？'),(285,'Which capability fits?','该选哪种能力？'),(365,'What counts as done?','怎样才算完成？')]:
        c+=document(70,y-24,MUTED)+txt(128,y+4,en,cn,21)
    c+=line('M 89 230 V 254',MUTED,True)+line('M 89 310 V 334',MUTED,True)
    c+=txt(65,466,'The user reconnects the steps.','由用户反复衔接各个环节。',18,MUTED)
    for y,en,cn,sub,subcn in [(188,'Goal + context','目标与上下文','Intent, sources, constraints','意图、来源与约束'),(278,'Select + execute','选择与执行','Eligible capabilities, dependencies','合格能力与任务依赖'),(368,'Verify + deliver','验证与交付','Acceptance criteria and evidence','验收条件与实际证据')]:
        c+=box(575,y,410,68,PALE,TEAL)+txt(594,y+27,en,cn,22,TEAL,600)+txt(594,y+52,sub,subcn,17,MUTED)
    c+=line('M 780 256 V 278')+line('M 780 346 V 368')
    c+=txt(575,466,'Each step serves the intended outcome.','每一步都服务于预期成果。',18,TEAL)
    save('diagrams/before-after.svg',1050,540,'Explicit coordination around the desired outcome','围绕预期成果的明确协调',c)


def interaction():
    c=heading('c','Autonomy with decision boundaries','有明确决策边界的自主执行','Illustrative interactions, not recorded runs or an interactive interface','交互示意，并非运行实录或可操作界面')
    # Equal columns and identical vertical anchors preserve comparison.
    panels=[('a','Clear task','明确任务',TEAL,PALE,[('User','用户','Fix within this scope.','在当前范围内修复。'),('Host + coordinating Skill','宿主与总控技能','Read → select → execute','读取 → 选择 → 执行'),('Tools → host','工具 → 宿主','Check the actual result.','核查实际结果。')],('Continue within authority','在授权范围内继续')),
    ('b','Ambiguous goal','目标存在歧义',AMBER,SAND,[('User','用户','Improve this module.','改进这个模块。'),('Host + coordinating Skill','宿主与总控技能','Local fix or redesign?','局部修复还是重设计？'),('User → host','用户 → 宿主','Agree on material changes.','确认实质性变更。')],('Only affected work waits','仅受影响工作等待')),
    ('c','Several capabilities','多种能力协同',BLUE,LILAC,[('User','用户','Review two modules.','审查两个模块。'),('Host + coordinating Skill','宿主与总控技能','Route available specialists.','选择可用专业能力。'),('Optional subagents → host','可选子代理 → 宿主','Return evidence to integrate.','回传证据供主代理整合。')],('Delegate only when allowed','委派必须获准'))]
    for i,(letter,en,cn,color,fill,steps,foot) in enumerate(panels):
        x=36+i*342
        c+=txt(x,130,letter,size=20,weight=700)+txt(x+30,130,en,cn,23,color,600)
        for j,(role,rolecn,msg,msgcn) in enumerate(steps):
            y=165+j*125
            c+=box(x,y,310,96,fill,color)+txt(x+17,y+31,role,rolecn,16,color,600)+txt(x+17,y+66,msg,msgcn,19)
            if j<2:c+=line(f'M {x+155} {y+96} V {y+125}',color)
        c+=txt(x,552,foot[0],foot[1],18,color,600)
    c+=txt(36,609,'Skills guide methods; tools act; supported, useful subagents are optional.','技能指导方法，工具执行操作；子代理按收益、环境支持与授权选择。',18,MUTED)
    save('diagrams/agent-interaction.svg',1080,645,'Three interaction patterns with decision boundaries','三类交互方式与决策边界',c)


def orchestration():
    c=heading('d','Composition follows dependencies','依据任务依赖组合能力','Illustrative report task; specialist Skills are not bundled','报告任务的逻辑示意；本包不附带专业技能')
    c+=node(350,116,350,'01','Shared contract','共同任务约定','Input, scope, acceptance','输入、范围与验收')
    c+=line('M 525 228 V 262 H 246 V 299')+line('M 525 262 H 804 V 299')
    c+=node(72,299,348,'02a','Data inspection','数据检查','Analysis Skill + file tools','分析技能 + 文件工具')
    c+=node(630,299,348,'02b','Method review','方法审查','Review Skill + source tools','审查技能 + 来源工具',BLUE,LILAC)
    c+=txt(525,348,'Independent','独立工作',19,MUTED,anchor='middle')+txt(525,377,'when feasible','可行时并行',17,MUTED,anchor='middle')
    c+=line('M 246 411 V 453 H 525 V 493')+line('M 804 411 V 453 H 525',BLUE,arrow=False)
    c+=node(350,493,350,'03','Integrate evidence','整合证据','Main agent checks conflicts','主代理核查冲突')
    c+=line('M 525 605 V 650')
    c+=box(72,650,906,105,'#f7f9fa',LINE)
    c+=txt(102,692,'Create report','生成报告',24,weight=600)+txt(444,692,'Verify','验证',24,weight=600)+txt(775,692,'Deliver','交付',24,weight=600)
    c+=line('M 292 685 H 412')+line('M 562 685 H 743')
    c+=txt(102,728,'Dependent on reconciled inputs','等待核对一致的输入',17,MUTED)+txt(444,728,'Current artifact + evidence','当前产物与证据',17,MUTED)+txt(775,728,'Disclose gaps','披露缺口',17,MUTED)
    c+=txt(72,807,'Delegation requires benefit, host support and authorization; a single agent can run this plan.','委派需要明确收益、宿主支持与授权；单个代理也可执行该计划。',17,MUTED)
    save('diagrams/orchestration.svg',1050,842,'Dependency-aware multi-capability orchestration','依据依赖关系编排多种能力',c)


def context_memory():
    c=heading('e','Context informs the task; experience informs the next','上下文服务当前任务，经验支持后续任务','A conditional information flow, not automatic access or background learning','有条件的信息流，不代表自动访问或后台学习')
    c+=txt(40,133,'Relevant sources','相关来源',23,weight=600)
    for y,en,cn in [(170,'Project files','项目文件'),(245,'Linked knowledge','关联知识库'),(320,'Provided history','已提供的历史摘要')]:
        c+=document(44,y,BLUE)+txt(100,y+30,en,cn,21)
    c+=line('M 290 267 H 361',BLUE)
    c+=box(362,190,264,150,LILAC,BLUE)
    c+=txt(384,230,'Access + relevance','访问与关联范围',23,BLUE,600)+txt(384,267,'Permission · availability','授权 · 可访问性',18)+txt(384,303,'Source · version · validity','来源 · 版本 · 有效性',17,MUTED)
    c+=line('M 626 267 H 690')
    c+=box(691,170,310,190,PALE,TEAL)+target(727,209)
    c+=txt(767,215,'Current task','当前任务',24,TEAL,600)+txt(714,270,'Goal → capabilities → action','目标 → 能力 → 行动',20)+txt(714,311,'Verify before claiming success','先验证，再报告完成',18,MUTED)
    c+=line('M 846 360 V 429',AMBER,True)
    c+=box(691,430,310,136,SAND,AMBER)+txt(713,468,'Save only when authorized','仅在获准时保存',21,AMBER,600)+txt(713,504,'Reliable, necessary records','可靠且必要的记录',18)+txt(713,540,'No default full-dialogue capture','不默认采集完整对话',16,MUTED)
    c+=line('M 691 499 H 626',AMBER,True)
    c+=box(362,430,264,136,BG,AMBER)+txt(384,468,'Eligible preferences','适用的偏好',22,AMBER,600)+txt(384,505,'Context + fit + freshness','结合任务、适配性与时效',17)+txt(384,540,'Never override hard limits','不覆盖硬约束与授权',17,MUTED)
    c+=line('M 362 499 H 289',AMBER,True)
    c+=box(40,430,248,136,BG,TEAL)+txt(62,468,'A later task','后续任务',23,TEAL,600)+txt(62,505,'Recheck before reuse','复用前重新核查',18)+txt(62,540,'Keep the user in control','用户始终保有控制权',17,MUTED)
    c+=txt(40,628,'Solid: task context     Dashed: optional persistence and reuse     Host interfaces are required.','实线：任务上下文    虚线：可选保存与复用    均依赖真实宿主接口。',18,MUTED)
    save('diagrams/context-memory.svg',1050,665,'Authorized context and experience reuse','获准的上下文与经验复用',c)


def main():
    global LANG
    for LANG in (0,1):
        for figure in (hero,workflow,comparison,interaction,orchestration,context_memory):figure()
    # Export a readable label index for translation review, generated from paired labels.
    (ROOT/'scripts/visuals_zh.json').write_text(json.dumps(LABELS,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Generated six academic schematics in English and Chinese (12 SVGs).')


if __name__=='__main__':main()
