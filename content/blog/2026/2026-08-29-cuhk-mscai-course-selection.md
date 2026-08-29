---
schema: bubblevan/v1
id: blog-20260829-cuhk-mscai-course-selection
content_kind: blog
title: CUHK MSc AI 2026/27 选课实录：CUSIS、CS-1、Consent 与 Add/Drop
date: 2026-08-29
updated: 2026-08-29
status: draft
visibility: public
summary: 记录 CUHK MSc AI 2026/27 从 8 月全年选课到 Term 1 Add/Drop 的实际流程：27 学分怎么拆、CUSIS 报错怎么理解、non-AIMS 课程为什么还要 webform 和 CS-1，以及截至 2026-08-29 我的真实已选课程与待处理事项。
topics: [CUHK, MSc AI, Course Selection, CUSIS, CS-1]
projects: [cuhk]
aliases: []
authors: [bubblevan]
---

8 月初第一次在 CUSIS 里选课时，我一度以为自己的选课已经“卡死”了。

AIMS5770 和 IERG5350 都显示：

```text
Department Consent Required.
```

AIMS5761 则直接报：

```text
由于未满足先决条件，因此无法添加此课程。
```

ROSE5760 又因为和已经选上的课程发生时间冲突而无法添加。再加上 non-AIMS elective 还要填 MSc AI Programme Office 的 webform 和 CS-1，我当时很难判断一门课到底是“没选上”“等学院处理”“已经满了”，还是“现在根本不该在 CUSIS 里选”。

到 2026-08-29，前面几个状态已经有了结果：AIMS5770、IERG5350 和 AIMS5761 都已经出现在 CUSIS 的 `Enrolled` 列表里。现在真正还差的是 Term 1 的一门 3 学分 non-AIMS elective。

这篇文章把这一个月里已经确认的规则、Programme Office 的回复和我自己的当前状态放到一起。它首先是一份给未来自己的状态记录；如果之后 Hermes 或其他 Agent 再读取这篇文章，应以文中的 `as_of` 日期和“已过时状态”列表为准，而不是继续沿用 8 月初的申请状态。

## 0. 给 Agent 看的当前状态快照

下面这段是我刻意保留的机器可读状态。后续如果选课结果变化，我应该优先更新这里和文末的“当前状态”，而不是只在正文中追加一段新描述。

```yaml
course_selection_state:
  as_of: 2026-08-29
  programme: CUHK MSc Artificial Intelligence
  cohort: 2026/27
  study_mode: full_time

  graduation_requirement:
    total_units: 27
    required_courses: 10
    core_electives: 6
    electives: 11

  current_credits:
    required_courses: 10
    core_electives: 6
    electives: 8
    total_enrolled: 24

  enrolled:
    term_1:
      - AIMS5701: 3
      - AIMS5702: 3
      - AIMS5710: 3
    term_2:
      - AIMS5703: 1
      - AIMS5704: 3
      - AIMS5730: 3
      - AIMS5770: 2
      - IERG5350: 3
    summer:
      - AIMS5761: 3

  term_1_non_aims_add_drop_preferences:
    first: SEEM5330 Speech and Language Processing
    second: FTEC5660 Agentic AI for Business and FinTech
    third: IEMS5719A Technology Strategy
    fourth: IERG5250 Edge AI and Applications
    webform_deadline: 2026-09-11
    expected_programme_add_limit: "at most one course, subject to availability and approval"

  special_courses:
    AIMS5780:
      status: not_enrolled
      rule: "apply only after securing a summer internship offer"
    AIMS5790:
      status: not_enrolled
      application_window: "during Term 1, 2026/27"
      details: "to be announced by MSc AI Programme Office"

  superseded_states:
    - "AIMS5770: Department Consent Required -> Enrolled"
    - "IERG5350: Department Consent Required -> Enrolled"
    - "AIMS5761: prerequisite error in CUSIS -> Enrolled through programme arrangement"
    - "ROSE5760: planned Term 2 fallback -> not needed; CUSIS reported a time conflict"

  unresolved:
    - "Term 1 non-AIMS elective final enrollment result"
    - "AIMS5790 application details and whether I will ultimately take it"
    - "The current conversation did not record whether the 2026-08-29 Term 1 add/drop webform was finally submitted after re-uploading signed CS-1 forms"
```

## 1. 27 学分到底怎么拆

CUHK MSc AI 的培养方案要求至少修满 27 units，分为三类：

| 类别 | 要求 | 我目前的状态 |
| --- | ---: | ---: |
| Required Courses | 10 | 10 / 10 |
| Core Elective Courses | 6 | 6 / 6 |
| Elective Courses | 11 | 8 / 11 |
| **总计** | **27** | **24 / 27** |

官方 Programme Structure：
<https://mscai.erg.cuhk.edu.hk/programme-structure>

Required Courses 是 AIMS5701、5702、5703、5704。我目前四门都已经 Enrolled，共 10 学分。

Core Elective 要至少修两门、共 6 学分。我目前是：

```text
AIMS5710 DL Fundamentals and Theories       3
AIMS5730 Natural Language Processing        3
                                             -
                                             6
```

Programme Office 还专门确认过：当 Core Elective 的最低 6 学分已经满足后，继续多修的 Core Elective 可以用于满足 Elective 的学分要求。因此“Core Elective”并不意味着超过 6 学分之后的课程一定浪费。

我的 Elective 目前已经有：

```text
AIMS5770 Adv. Topics in AI (I)              2
IERG5350 Reinforcement Learning             3
AIMS5761 BP to Investable AI Ventures       3
                                             -
                                             8
```

所以截至 2026-08-29，我缺的不是“5 学分”“Summer 必修”或者“还要再凑很多课”，而是最后 **3 学分 Elective**。这也是为什么 Term 1 Add/Drop 的 non-AIMS webform 对我很重要：四个志愿里只要最终成功加入一门 3 学分课，总学分就是 27。

## 2. 8 月的 Course Registration 和 9 月 Add/Drop 不是一回事

我最开始混淆的是时间线。

2026/27 的全校 Course Registration 在 2026-08-04 10:00 到 2026-08-07 17:30。Graduate School 把这一阶段定义为整个 academic year 的课程注册，不只是 Term 1。

官方页面：
<https://www.gs.cuhk.edu.hk/academics/course-selection-add-drop/2026-27-exercise>

之后每个 Term 还有自己的 Add/Drop。Term 1 对 MSc AI 来说是 9 月开学后的窗口，Programme Office 发给我的通知写的是：

```text
Add/drop period for Term 1, 2026/27:
7 – 21 September 2026
```

Graduate School 的通用 schedule 还会按 programme 分成不同 batch，所以实际操作时应当以自己 programme 的邮件、CUSIS Enrolment Date 和 Graduate School schedule 共同确认，不能只记住“九月前两周”这样一个模糊结论。

官方 Schedule：
<https://www.gs.cuhk.edu.hk/academics/course-selection-add-drop/2026-27/schedule>

这也解释了为什么 8 月初没有拿到一门 non-AIMS elective 并不意味着这一年就再也没机会。MSc AI 在 Term 1 Add/Drop 前又发了新的 webform，让学生重新提交第一到第四志愿。

## 3. 为什么 CUSIS 之外还有 MSc AI webform

如果只看 CUSIS，很容易以为所有课程都应该由学生自己点 `Enroll`。

实际并不是这样。

我遇到的课程至少可以分成三种处理方式：

1. 已经在 Study Scheme 内、可以正常通过 CUSIS 管理的课程；
2. 需要 Programme / Department consent，由 MSc AI Office 或开课部门进一步处理的课程；
3. non-AIMS elective，需要 Programme Office 的 webform + CS-1，再由开课部门审批。

Graduate School 的通用规则是：大部分研究生在 CUSIS 选课；超出 prescribed study scheme 的课程需要 CS-1。MSc AI 在此基础上又用 programme webform 收集 elective priority，方便统一向其他 department 申请名额。

Graduate School General Information：
<https://www.gs.cuhk.edu.hk/academics/course-selection-add-drop/general-information>

这一点在 2026-08-29 的 Term 1 新 webform 里写得尤其清楚：

- 可以填 1st 到 4th Priority；
- 如果 webform 与 CS-1 写法不一致，**以 webform 的选择为准**；
- 除非修改志愿，否则不要重复提交；
- priority 会根据 **最近一次提交的 timestamp** 确定；
- enrolment 取决于 quota 和 course-offering department approval；
- 结果可能在 Add/Drop 结束之后才出来；
- webform submission 本身不保证最终 enrolment；
- Programme Office 预计 Add/Drop 期间每名学生最多加入一门 non-AIMS elective。

因此，webform 不是一个“填了就选上”的替代 CUSIS 页面。它更像 MSc AI Programme Office 收集申请顺序并向其他 department 处理名额的入口。

## 4. `Department Consent Required` 不是“选课失败”

我第一次看到下面这条错误时，把它理解成了“我不满足条件”：

```text
Department Consent Required.
您必须具有选修此课程的权限。
```

AIMS5770 和 IERG5350 都出现过这个状态。

Graduate School FAQ 对这条信息的解释是：需要先取得 Programme / Graduate Division 的 approval，而不是说课程本身已经拒绝我。

FAQ：
<https://www.gs.cuhk.edu.hk/academics/course-selection-add-drop/faq>

AIMS5770 的情况更具体。我曾经邮件问 Programme Office：

```text
Is there a specific enrolment sequence or approval required for AIMS5770?
```

Programme Office 的回复是，他们会按照我提交的 webform 处理 enrollment request。

结果也验证了这一点：到 2026-08-29，AIMS5770 已经从 `Department Consent Required` 变成：

```text
Enrolled
2.00 units
Graded
```

IERG5350 也经历了类似变化，现在同样已经是：

```text
Enrolled
3.00 units
Graded
```

所以以后再遇到 `Department Consent Required`，第一反应不应该是反复在 CUSIS 里点击 Enroll，而是先看 Programme Office 有没有已经提供 webform、permission 流程或专门说明。

## 5. AIMS5761 的 prerequisite error 为什么最后没有阻止我选上

AIMS5761 是另一个容易误判的例子。

我直接在 CUSIS 尝试时得到：

```text
由于未满足先决条件，因此无法添加此课程。

Pre-requisite:
AIMS5760 or IEMS5712 or IERG5340;
A team with AI application ideas for commercialization in mind
```

如果只看 CUSIS，我当时会得出结论：Summer 这门 3 学分课没法选。

但是 MSc AI 的 elective webform 在 AIMS5761 后面专门写了一条 programme-specific note：

```text
Please disregard the prerequisite for AIMS5761 in CUSIS.
You are free to enroll in AIMS5761 by choosing it here, space permitted.
```

后来 CUSIS 的实际结果是：

```text
AIMS5761 BP to Investable AI Ventures
Status: Enrolled
Units: 3.00
```

这个坑的经验不是“CUSIS 的 prerequisite 可以无视”。正确结论只能限定在这一次：**当 Programme Office 对某门课明确给出 override / special arrangement 时，应按 Programme Office 的说明操作。** 没有这类书面说明时，CUSIS prerequisite 仍然应该当作真实限制。

## 6. 时间冲突和 quota 才是另一类真正的阻塞

ROSE5760 的报错不是 consent，而是：

```text
由于与课程 1544 存在时间冲突，因此无法添加此课程。
请选择其他课程。
```

Class 1544 是我已经 Enrolled 的 AIMS5703。

Graduate School FAQ 把 time conflict 定义为目标课程与 shopping cart 或 enrolled class 的上课时间冲突。这种情况不能靠“等 Programme Office consent”自动消失，除非课程时间、已有选课或 programme arrangement 发生变化。

另一个常见状态是 `Closed`。FAQ 对 closed class 的解释是 class 已满；如果该 class 开放 waitlist，可以选择加入 waitlist。这里也要区分：

```text
Closed / Class is full
```

和：

```text
Department Consent Required
```

前者首先是 quota 问题，后者首先是 approval 问题。我 8 月初把它们混在一起理解，导致对很多课程的成功概率判断都不准确。

## 7. Summer Session 不是毕业必修

我最早因为 Elective 要 11 学分，而大部分课程都是 3 学分，一度以为必须在 Summer 再修一门课才能毕业。

Programme Office 后来明确回复：

```text
It is not a must for students to take courses during Summer Session.
```

所以 Summer Session 本身不是 MSc AI 的毕业要求。真正的要求仍然是 study scheme 中的 27 units 和各 category 的学分。

我现在保留 AIMS5761，是因为它已经成功 Enrolled，而且刚好贡献 3 个 Elective units；这和“所有学生都必须上 Summer”是两件事。

如果一个学生在 Term 1 和 Term 2 已经按 study scheme 修满毕业要求，可以不依靠 Summer 来凑学分。

## 8. AIMS5780 Internship 要先拿 offer，再申请课程

AIMS5780 也不能理解成“选了这门课，学校就会给我安排一个实习”。

Programme Office 的回复是：

```text
Students could submit application for internship course
after they secured an offer of summer internship.
```

也就是说顺序是：

```text
自己拿到 summer internship offer
        ↓
再申请 AIMS5780
        ↓
Programme 审核后决定是否 enrol
```

官方 course description 还写明，这门课要求学生在 study-related position 实习不少于 12 周，并有 academic supervisor 和 industry co-supervisor，结束后提交 internship report。

课程说明：
<https://mscai.erg.cuhk.edu.hk/course-list-and-descriptions>

因此，如果我只是自己去实习，但不需要把它计入学分，并不需要为了“有实习经历”本身提前占一个 AIMS5780 名额。没有拿到 offer 的学生也不会被 enroll 进这门课。

## 9. AIMS5790 Project I 也不是 8 月普通选课

我很愿意修 AIMS5790，因为它更接近一个 supervised AI project：在 academic staff 指导下设计、研究和开发项目，最后做 presentation 并提交 project report。

但它不是 8 月 Course Registration 时直接抢的普通 elective。

Programme Office 给我的时间说明是：

```text
Application for AIMS5790 will be open during Term 1, 2026/27
and details will be provided during New Students Orientation.
```

所以截至 2026-08-29：

```text
AIMS5790 = 我有兴趣，但尚未申请，也没有 Enrolled。
```

如果 Term 1 的 non-AIMS elective 成功，我的总学分已经能达到 27。之后是否再选 AIMS5790 就变成“要不要额外做项目”的选择，而不是毕业学分缺口的补救措施。

Programme Office 在 8 月的邮件中还提醒全日制学生整个 normative study period 最多可修 31 units。这个上限属于 programme 当年安排，后续如果真的申请 AIMS5790，我仍会在申请时重新确认最新规则，而不会只依赖这篇文章。

## 10. CS-1 到底怎么填

Graduate School 的 CS-1 全名是：

```text
Application for Course Selection Outside the Prescribed Study Scheme
```

下载：
<https://www.gs.cuhk.edu.hk/download/CS1.pdf>

我之前最容易混淆的是 `Course Code`、`Subject Area`、`Catalog No.` 和 `Section`。

例如：

```text
SEEM5330
```

应拆成：

```text
Subject Area: SEEM
Catalog No.: 5330
Section: 留空
Unit: 3
```

而：

```text
IEMS5719A
```

应拆成：

```text
Subject Area: IEMS
Catalog No.: 5719
Section: A
Unit: 3
```

`A` 是 section，不属于 Catalog No.

我 2026-08-29 准备的两份 CS-1 是：

| 表格 | 课程 |
| --- | --- |
| CS1-Term1.pdf | SEEM5330、FTEC5660、IEMS5719A |
| CS1-Term1 IERG5250.pdf | IERG5250 |

原因很简单：CS-1 一页只有三行，所以第四门只能放到第二份表。

另一个很容易漏的是页面底部的：

```text
Signature of Student
Date
```

我上传检查的版本里 Date 已填写为 `2026.8.29`，但 Student Signature 仍为空。因此这两份文件在真正提交前还需要补学生签名。后面的 Course Teacher / Department Approval、Programme Director endorsement 和 Head of Graduate Division approval 不是我自己替他们填写的部分。

## 11. Term 1 Add/Drop 我现在为什么排这四门

2026-08-29 的新 webform 允许填四个 non-AIMS elective priority。我目前的顺序是：

```text
1. SEEM5330 Speech and Language Processing
2. FTEC5660 Agentic AI for Business and FinTech
3. IEMS5719A Technology Strategy
4. IERG5250 Edge AI and Applications
```

这里必须区分“选课前调研”和“上完课后的课程评价”。截至本文日期，我没有修过这四门，因此下面只是申请前的信息，不应被 Hermes 或读者当成我的实修结论。

### SEEM5330

这是我目前的第一志愿。官方课程内容明显包含 speech production / perception、speech signal processing、统计方法、ASR、TTS 和 spoken language systems，因此它并不是一门纯 LLM 文本课。

我已经在 Term 2 选了 AIMS5730 NLP，所以 SEEM5330 的价值更多在 speech / ASR / TTS 这条分支，而不是简单重复 NLP。

### FTEC5660

这是第二志愿。课程名是 Agentic AI for Business and FinTech，我目前查到的公开学生 coursework 确实涉及 agent、RAG、tool calling、MCP、financial analysis agent 和 project，因此它并不能简单用另一门 FinTech AI 课程的差评代替评价。

我仍把它放在 SEEM5330 后面，因为实际 workload 和 2026/27 的最终考核安排还有不确定性。

### IEMS5719A

这是第三志愿。课程定位偏 Technology Strategy，而不是 AI 技术课。

我从学生评价里得到的信息是：强制出勤较严格，晚课会持续到 22:00，但课外 workload 较少。这个评价目前只有单一学生来源，所以我只把它当作风险参考，不能写成确定事实。

CS-1 里要特别注意：

```text
Subject Area: IEMS
Catalog No.: 5719
Section: A
Unit: 3
```

### IERG5250

这是第四志愿。官方主题包括 Edge AI、accelerator / FPGA、cloud-edge、model compression、安全隐私和相关应用。

我目前找到的学生评价提到 project、两次答辩、report、paper review、presentation 和 survey，且自学比例较高。这个信息同样属于学生经验，不是 2026/27 官方 assessment scheme，因此这里只用于排序时评估 workload 风险。

## 12. 有几条旧信息现在必须明确作废

这部分是写给未来自己的，也是为了防止 Agent 继续拿旧状态做推荐。

### 已作废 1：AIMS5770 还在等 Department Consent

作废。

当前：

```text
AIMS5770 = Enrolled, 2 units
```

### 已作废 2：IERG5350 还在申请

作废。

当前：

```text
IERG5350 = Enrolled, 3 units
```

### 已作废 3：AIMS5761 因 prerequisite 无法选

作废。

那是直接在 CUSIS 尝试时的错误。MSc AI webform 明确允许忽略该 prerequisite 并通过 programme arrangement 申请；现在：

```text
AIMS5761 = Enrolled, 3 units
```

### 已作废 4：我需要靠 ROSE5760 补 Term 2 elective

作废。

IERG5350 已经 Enrolled；ROSE5760 当时又和 AIMS5703 存在 time conflict，因此它已经不再是当前选课计划的一部分。

### 已作废 5：Summer 是为了毕业必须选

作废。

Programme Office 已经明确 Summer Session 不是 must。

## 13. 截至 2026-08-29，我下一步只剩什么

当前已经确认 Enrolled 的课程合计 24 学分：

```text
Term 1:  9
Term 2: 12
Summer:  3
          --
          24
```

按 category 看：

```text
Required     10 / 10
Core          6 / 6
Elective      8 / 11
```

所以当前最直接的任务是完成 Term 1 non-AIMS Add/Drop 申请，并争取四个志愿中的一门 3 学分课程。

当前 priority：

```text
SEEM5330
  > FTEC5660
  > IEMS5719A
  > IERG5250
```

Programme Office 的新 webform 截止到 2026-09-11，而且明确说明最多预计给每名学生添加一门、最终还要看 quota 和开课 department approval。

我已经准备了对应 CS-1，但在当前记录中，2026-08-29 上传检查的 PDF 版本还缺 `Signature of Student`。同时，这段对话并没有明确记录我在补签并重新上传后是否最终点击了 webform 的 `Submit`。

因此下一次更新这篇文章时，第一件事不是重新研究一遍整个培养方案，而是只更新两个字段：

```text
1. Term 1 webform: submitted / not submitted
2. Final non-AIMS elective: 哪一门真正变成 Enrolled
```

如果最终增加一门 3 学分 elective：

```text
24 + 3 = 27
```

毕业最低学分要求就会在当前课程计划中满足。AIMS5790 之后是否申请、AIMS5780 是否因为拿到 summer internship offer 而申请，都属于后续选择，不再是当前的学分缺口。

## 官方入口

- MSc AI Programme Structure  
  <https://mscai.erg.cuhk.edu.hk/programme-structure>
- MSc AI Course List and Descriptions  
  <https://mscai.erg.cuhk.edu.hk/course-list-and-descriptions>
- Graduate School 2026/27 Course Selection & Add/Drop Exercise  
  <https://www.gs.cuhk.edu.hk/academics/course-selection-add-drop/2026-27-exercise>
- Graduate School 2026/27 Schedule  
  <https://www.gs.cuhk.edu.hk/academics/course-selection-add-drop/2026-27/schedule>
- Graduate School Course Selection FAQ  
  <https://www.gs.cuhk.edu.hk/academics/course-selection-add-drop/faq>
- Form CS-1  
  <https://www.gs.cuhk.edu.hk/download/CS1.pdf>
