---
layout: default
title: "Horizon Summary: 2026-07-04 (EN)"
date: 2026-07-04
lang: en
---

> From 17 items, 13 important content pieces were selected

---

1. [SearXNG: A Free Open-Source Metasearch Engine](#item-1) ⭐️ 8.0/10
2. [EU Parliament Member Hacked with Pegasus Spyware](#item-2) ⭐️ 8.0/10
3. [Ubicloud Advocates Strict Memory Overcommit for PostgreSQL](#item-3) ⭐️ 8.0/10
4. [Open Source AI Gap Map Launched by Current AI](#item-4) ⭐️ 8.0/10
5. [Guide to Running SOTA LLMs Locally Sparks Cost Debate](#item-5) ⭐️ 7.0/10
6. [Costco's Anti-Amazon Strategy: Avoid Last-Mile](#item-6) ⭐️ 7.0/10
7. [Africans Embrace Starlink as Leapfrog Technology](#item-7) ⭐️ 7.0/10
8. [Factories Are Just Rooms: A Mindset Shift](#item-8) ⭐️ 7.0/10
9. [Course Sales Plunge 50%+ as AI Disrupts Developer Education](#item-9) ⭐️ 7.0/10
10. [DeepMind & A24 Partner on AI-Film Research](#item-10) ⭐️ 7.0/10
11. [Claude Code v2.1.200: Bug fixes and manual permission mode](#item-11) ⭐️ 6.0/10
12. [FIDE sanctions Kramnik for baseless cheating allegations](#item-12) ⭐️ 6.0/10
13. [Let AI coding assistants use their own judgment](#item-13) ⭐️ 6.0/10

---

<a id="item-1"></a>
## [SearXNG: A Free Open-Source Metasearch Engine](https://github.com/searxng/searxng) ⭐️ 8.0/10

SearXNG is a free, open-source internet metasearch engine that aggregates results from multiple search engines while respecting user privacy. It has been actively maintained since forking from the discontinued Searx, with over 70 public instances available. SearXNG provides a privacy-focused alternative to centralized search engines, allowing users to avoid tracking and profiling. It is also a key tool for developers building AI agents and RAG applications that require private, self-hosted search capabilities. SearXNG supports JSON output, making it suitable for integration with AI agents and RAG pipelines. Users can self-host it via Docker or use public instances, though some users report occasional CAPTCHA blocks from upstream search engines like DuckDuckGo.

hackernews · theanonymousone · Jul 3, 20:15 · [Discussion](https://news.ycombinator.com/item?id=48779454)

**Background**: A metasearch engine aggregates results from multiple search engines without maintaining its own index. SearXNG is a fork of the original Searx, which was discontinued; it is free and open-source software that does not track or profile users. It can be self-hosted to ensure complete privacy control.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Metasearch_engine">Metasearch engine</a></li>
<li><a href="https://en.wikipedia.org/wiki/SearXNG">SearXNG - Wikipedia</a></li>
<li><a href="https://github.com/searxng/searxng">GitHub - searxng/searxng: SearXNG is a free internet metasearch engine which aggregates results from various search services and databases. Users are neither tracked nor profiled. · GitHub</a></li>

</ul>
</details>

**Discussion**: The original Searx creator noted he is no longer involved due to limitations of the metasearch concept, and pointed to his new project Hister. Users praised SearXNG for daily use and integration with AI agents, but noted slower results and occasional CAPTCHA blocks as trade-offs for privacy.

**Tags**: `#search engine`, `#privacy`, `#open source`, `#metasearch`, `#self-hosted`

---

<a id="item-2"></a>
## [EU Parliament Member Hacked with Pegasus Spyware](https://citizenlab.ca/research/member-of-committee-investigating-spyware-hacked-with-pegasus/) ⭐️ 8.0/10

Citizen Lab investigation found that a member of the European Parliament's committee investigating spyware had their iPhone infected with NSO Group's Pegasus spyware on multiple occasions in 2022 and 2023. This incident highlights the threat of state-sponsored spyware targeting democratic institutions and elected officials, undermining the security and integrity of the European Parliament. The first infection in October 2022 overlapped with a known Pegasus campaign targeting exiled journalists from Russia and Belarus in Europe, suggesting a Pegasus customer with cross-border authorization was responsible.

hackernews · ledoge · Jul 3, 20:38 · [Discussion](https://news.ycombinator.com/item?id=48779683)

**Background**: Pegasus is a commercial spyware developed by Israeli firm NSO Group, capable of remotely compromising mobile devices to extract data, record calls, and activate microphones. Citizen Lab is a University of Toronto research lab that investigates digital threats to human rights.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Pegasus_(spyware)">Pegasus (spyware)</a></li>
<li><a href="https://en.wikipedia.org/wiki/Citizen_Lab">Citizen Lab</a></li>

</ul>
</details>

**Discussion**: Commenters noted that Greece has an ongoing Pegasus scandal involving the prime minister's office, and some European countries have abused spyware so much that Israeli firms cut ties. There was also debate about whether the EU parliament lacks policies separating work and personal devices.

**Tags**: `#cybersecurity`, `#spyware`, `#Pegasus`, `#surveillance`, `#European Parliament`

---

<a id="item-3"></a>
## [Ubicloud Advocates Strict Memory Overcommit for PostgreSQL](https://www.ubicloud.com/blog/postgresql-and-the-oom-killer-why-we-use-strict-memory-overcommit) ⭐️ 8.0/10

Ubicloud published a blog post explaining why they use strict memory overcommit (vm.overcommit_memory=2) for PostgreSQL to prevent the Linux OOM killer from terminating the database process. This practice can significantly improve PostgreSQL stability under memory pressure, which is critical for managed database providers and any production deployment relying on PostgreSQL. The article recommends setting vm.overcommit_memory to 2 (strict overcommit) and adjusting vm.overcommit_ratio to reserve memory for the OS and other processes, but warns that mode 2 can prevent fork() calls if memory is exhausted.

hackernews · furkansahin · Jul 3, 13:00 · [Discussion](https://news.ycombinator.com/item?id=48774509)

**Background**: Linux uses memory overcommit by default, allowing processes to allocate more virtual memory than physical RAM, which can trigger the OOM killer when memory is exhausted. The OOM killer selects and kills a process to free memory, often targeting PostgreSQL due to its large memory footprint. Strict overcommit (mode 2) refuses allocations that exceed the sum of RAM and swap, preventing overcommit but requiring careful configuration.

<details><summary>References</summary>
<ul>
<li><a href="https://www.kernel.org/doc/Documentation/vm/overcommit-accounting">The Linux kernel supports the following overcommit handling modes</a></li>
<li><a href="https://www.cybertec-postgresql.com/en/what-you-should-know-about-linux-memory-overcommit-in-postgresql/">What you should know about Linux memory overcommit in PostgreSQL</a></li>
<li><a href="https://last9.io/blog/understanding-the-linux-oom-killer/">Linux OOM Killer : A Detailed Guide to Memory Management | Last9</a></li>

</ul>
</details>

**Discussion**: Community members caution that mode 2 can break applications that rely on fork() and recommend thorough testing before production deployment. Some users share experiences of instability when mixing strict overcommit with applications that allocate large virtual memory, like Go programs.

**Tags**: `#PostgreSQL`, `#Linux`, `#Memory Management`, `#OOM Killer`, `#Database Operations`

---

<a id="item-4"></a>
## [Open Source AI Gap Map Launched by Current AI](https://simonwillison.net/2026/Jul/3/open-source-ai-gap-map/#atom-everything) ⭐️ 8.0/10

Current AI, a non-profit founded at the AI Action Summit in Paris in February 2025, launched the Open Source AI Gap Map v0.1, indexing 421 open source AI products across models, tools, datasets, and hardware, with underlying data released under an MIT license on GitHub. This map provides a structured, comprehensive view of the open source AI ecosystem, helping identify gaps and guide investment, which is crucial for fostering a public option for AI and reducing dependency on proprietary systems. The map details 421 products from 228 organizations, organized into 14 categories across 3 layers (model components, product/UX, infrastructure), and tracks 16,185 GitHub repos. The data is available as 1,184 YAML files and can be explored via Datasette Lite.

rss · Simon Willison · Jul 3, 22:04

**Background**: Current AI is a global non-profit partnership backed by $400 million in committed capital, aiming to build a public option for AI. The open source AI ecosystem has grown rapidly but lacks a comprehensive mapping, making it hard to identify gaps in areas like hardware, datasets, and tools.

<details><summary>References</summary>
<ul>
<li><a href="https://map.currentai.org/">Current AI – Open Source AI Gap Map</a></li>

</ul>
</details>

**Tags**: `#open source`, `#AI`, `#ecosystem mapping`, `#non-profit`

---

<a id="item-5"></a>
## [Guide to Running SOTA LLMs Locally Sparks Cost Debate](https://github.com/jamesob/local-llm) ⭐️ 7.0/10

Jamesob published a guide on GitHub detailing how to build expensive local setups for running state-of-the-art LLMs, with budgets starting around $40,000 and using multiple high-end GPUs. This guide highlights the extreme cost and hardware requirements of running top-tier LLMs locally, sparking community debate on whether such setups are cost-effective compared to API subscriptions like Claude Opus at $200/month. The proposed build includes four GPUs at $12,000 each, pushing the total cost to $50,000–$55,000, and relies on quantization and pruning techniques to fit models like GLM-5.2 into available VRAM.

hackernews · livestyle · Jul 3, 15:03 · [Discussion](https://news.ycombinator.com/item?id=48775921)

**Background**: Running large language models locally requires significant GPU memory and compute power. State-of-the-art models like GPT-4 or Claude Opus typically need multiple high-end GPUs (e.g., H100, H200) with hundreds of GB of VRAM, costing tens of thousands of dollars. Quantization reduces model precision to lower memory usage, but can degrade output quality.

<details><summary>References</summary>
<ul>
<li><a href="https://www.geeksforgeeks.org/deep-learning/recommended-hardware-for-running-llms-locally/">Recommended Hardware for Running LLMs Locally - GeeksforGeeks</a></li>
<li><a href="https://www.pugetsystems.com/labs/articles/tech-primer-what-hardware-do-you-need-to-run-a-local-llm/">Tech Primer: What hardware do you need to run a local LLM?</a></li>

</ul>
</details>

**Discussion**: Commenters largely criticize the cost, noting that $40,000–$55,000 could cover 16+ years of Claude Opus API access. Some suggest intermediate options like unified memory architectures with 128GB VRAM for running models like DeepSeek V4 at good speed. Others question the real-world performance of heavily quantized and pruned models.

**Tags**: `#LLM`, `#local deployment`, `#hardware`, `#cost analysis`

---

<a id="item-6"></a>
## [Costco's Anti-Amazon Strategy: Avoid Last-Mile](https://phenomenalworld.org/analysis/the-anti-amazon/) ⭐️ 7.0/10

A new analysis argues that Costco's success comes from deliberately avoiding the complexity of last-mile delivery, instead relying on bulk sales and customer self-transport. This contrast highlights fundamental strategic trade-offs in retail logistics, showing that avoiding last-mile delivery can be a viable competitive advantage against e-commerce giants like Amazon. Costco's model involves freight trucks delivering to warehouses, where customers buy in bulk and transport goods home themselves, eliminating the need for costly individual home deliveries.

hackernews · bookofjoe · Jul 3, 15:14 · [Discussion](https://news.ycombinator.com/item?id=48776044)

**Background**: Last-mile delivery refers to the final step of the delivery process from a distribution center to the customer's door. It is often the most expensive and logistically complex part of e-commerce, involving challenges like route optimization, failed deliveries, and high fuel costs. Costco's warehouse club model bypasses this entirely by having customers come to the store.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Last_mile_(transportation)">Last mile (transportation) - Wikipedia</a></li>
<li><a href="https://anchanto.com/last-mile-delivery-challenges-solutions/">What Is Last Mile Delivery and How to Overcome its Challenges</a></li>
<li><a href="https://www.businessinsider.com/why-costcos-business-model-is-so-great-2016-2">Costco is beating Walmart and Amazon with the 'best business model' in retail</a></li>

</ul>
</details>

**Discussion**: Commenters praised the analysis, with one quoting a proverb about wise people avoiding problems. Others noted that Costco's model is tied to car-centric suburbs, and some shared personal shopping habits that mix different stores and transport modes.

**Tags**: `#business strategy`, `#logistics`, `#e-commerce`, `#retail`, `#economics`

---

<a id="item-7"></a>
## [Africans Embrace Starlink as Leapfrog Technology](https://www.economist.com/middle-east-and-africa/2026/07/02/africans-are-turning-to-starlink) ⭐️ 7.0/10

Africans are increasingly adopting Starlink satellite internet to bypass poor terrestrial infrastructure, mirroring the continent's earlier leapfrog to mobile phones. This adoption could significantly narrow the digital divide in underserved regions, providing reliable internet access where traditional ISPs have failed. Starlink, a SpaceX subsidiary, operates a low Earth orbit satellite constellation delivering broadband with speeds up to 220 Mbps, and is now available in approximately 160 countries.

hackernews · bookofjoe · Jul 3, 21:08 · [Discussion](https://news.ycombinator.com/item?id=48779977)

**Background**: Leapfrogging occurs when developing regions skip older technologies (e.g., landlines) and adopt newer ones (e.g., mobile phones). Africa famously leapfrogged wired telephony to mobile, and Starlink offers a similar path for internet access, bypassing the need for extensive fiber or cable infrastructure.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Starlink">Starlink - Wikipedia</a></li>
<li><a href="https://starlink.com/technology">Starlink | Technology</a></li>
<li><a href="https://en.wikipedia.org/wiki/Leapfrogging">Leapfrogging - Wikipedia</a></li>

</ul>
</details>

**Discussion**: Commenters shared personal experiences: one former Starlink engineer expressed pride in bringing internet to unserved areas; others in South Africa and rural US noted Starlink's reliability during power outages and its value where traditional options are slow or unavailable. The discussion drew parallels to Africa's mobile phone leapfrogging.

**Tags**: `#Starlink`, `#Africa`, `#satellite internet`, `#digital divide`, `#technology adoption`

---

<a id="item-8"></a>
## [Factories Are Just Rooms: A Mindset Shift](https://interconnected.org/home/2026/07/03/factories) ⭐️ 7.0/10

An essay argues that factories are fundamentally just rooms, encouraging a mindset shift towards simplicity and adaptability in manufacturing. This challenges conventional thinking about manufacturing, suggesting that complex, specialized facilities may not be necessary, which could lower barriers to entry and foster innovation. The essay is published on interconnected.org with a score of 7.0/10, tagged with manufacturing, systems thinking, simplicity, and engineering culture.

hackernews · arbesman · Jul 3, 15:13 · [Discussion](https://news.ycombinator.com/item?id=48776035)

**Background**: Factories are often viewed as complex, capital-intensive facilities with specialized machinery. The essay reframes them as simple rooms, emphasizing that the key is the process and people, not the physical infrastructure.

**Discussion**: Community comments include personal anecdotes about running small factories and kitchens as factories, with some agreeing that simplicity is valuable but noting that it may not always lead to business success.

**Tags**: `#manufacturing`, `#systems thinking`, `#simplicity`, `#engineering culture`

---

<a id="item-9"></a>
## [Course Sales Plunge 50%+ as AI Disrupts Developer Education](https://simonwillison.net/2026/Jul/3/josh-w-comeau/#atom-everything) ⭐️ 7.0/10

Josh W. Comeau reports that his new course launch is on track to sell only one-third of typical copies, and his existing courses have seen sales drop over 50% year-over-year, which he attributes to AI-induced career uncertainty and LLMs replacing paid educational content. This trend signals a structural shift in the developer education market, where AI both reduces demand for learning due to career fears and substitutes paid courses with free LLM-based tutoring, threatening the livelihood of independent course creators. Comeau spoke with multiple course creators who all observed similar declines of 50%+ in revenue and engagement, with learners increasingly turning to LLMs that consume creators' work without consent or compensation.

rss · Simon Willison · Jul 3, 21:25

**Background**: Developer education has long relied on paid courses and tutorials, but the rise of large language models (LLMs) like GPT-4 and Gemini now offers personalized, on-demand tutoring at low or no cost. Meanwhile, rapid AI advancements have fueled uncertainty about the future of software development jobs, discouraging investment in new skills.

<details><summary>References</summary>
<ul>
<li><a href="https://medium.com/@keshavarangarajan/the-impact-of-llms-on-learning-and-education-3cd2a8367c23">The Impact of LLMs on Learning and Education | by keshava rangarajan | Medium</a></li>
<li><a href="https://www.thirdrocktechkno.com/blog/llm-based-tutors/">Can AI Really Replace Teachers? LLMs in Education | 2026</a></li>
<li><a href="https://shecancode.io/from-uncertainty-to-opportunity-how-women-in-tech-can-ride-this-wave-rather-than-be-engulfed-by-it/">From uncertainty to opportunity: How women in tech ... - SheCanCode</a></li>

</ul>
</details>

**Tags**: `#AI impact`, `#developer education`, `#course sales`, `#LLMs`, `#tech industry trends`

---

<a id="item-10"></a>
## [DeepMind & A24 Partner on AI-Film Research](https://deepmind.google/blog/google-deepmind-and-a24-announce-first-of-its-kind-research-partnership/) ⭐️ 7.0/10

Google DeepMind and independent film studio A24 announced a first-of-its-kind research partnership to explore how AI can be used in filmmaking and storytelling. This partnership signals a potential paradigm shift in AI-driven storytelling, bridging cutting-edge AI research with a prestigious creative studio, which could lead to new tools and methods for filmmakers. The partnership is described as a research collaboration, not a commercial deal, and will focus on exploring AI's creative potential in filmmaking. No specific projects or timelines have been disclosed.

rss · DeepMind Blog · Jul 3, 14:25

**Background**: Google DeepMind is a leading AI research lab known for breakthroughs like AlphaGo and AlphaFold. A24 is an independent entertainment company famous for critically acclaimed films such as 'Everything Everywhere All at Once'. This partnership marks one of the first formal research collaborations between a major AI lab and a film studio.

**Tags**: `#AI`, `#DeepMind`, `#research partnership`, `#film`, `#A24`

---

<a id="item-11"></a>
## [Claude Code v2.1.200: Bug fixes and manual permission mode](https://github.com/anthropics/claude-code/releases/tag/v2.1.200) ⭐️ 6.0/10

Anthropic released Claude Code v2.1.200, which fixes multiple bugs and changes the default permission mode from Normal to Manual. This release improves reliability and security by preventing unintended auto-continuation of actions and reducing the risk of unauthorized operations. The update fixes crashes related to MCP server configuration, background session stalls, daemon lock file conflicts, and subagent rate-limit handling, among others.

github · ashwin-ant · Jul 3, 16:52

**Background**: Claude Code is Anthropic's CLI tool for AI-assisted coding. It supports permission modes to control what actions the AI can perform automatically. The default mode was previously 'Normal', which allowed automatic file edits and command execution; the new 'Manual' mode requires user approval for each action.

<details><summary>References</summary>
<ul>
<li><a href="https://docs.anthropic.com/en/docs/claude-code/cli-reference">Complete reference for Claude Code command - line interface ...</a></li>
<li><a href="https://claudefa.st/blog/guide/development/permission-management">Claude Code Permissions : Safe vs Fast Development Modes</a></li>
<li><a href="https://code.claude.com/docs/en/mcp">Connect Claude Code to tools via MCP - Claude Code Docs</a></li>

</ul>
</details>

**Tags**: `#claude-code`, `#release`, `#bug-fix`, `#cli`

---

<a id="item-12"></a>
## [FIDE sanctions Kramnik for baseless cheating allegations](https://www.fide.com/fide-ethics-disciplinary-commission-issues-a-decision-in-case-involving-gm-vladimir-kramnik/) ⭐️ 6.0/10

FIDE's Ethics and Disciplinary Commission has sanctioned former world chess champion Vladimir Kramnik for making unfounded cheating allegations against other players, including grandmasters Daniel Naroditsky and Hikaru Nakamura. This decision sets a precedent for accountability in chess, deterring prominent figures from using their influence to spread harmful accusations without evidence, and protects the integrity of the sport. The specific sanctions imposed on Kramnik have not been detailed in the summary, but the case highlights the ongoing tension around online cheating detection methods and the need for statistical rigor.

hackernews · DarkContinent · Jul 3, 17:04 · [Discussion](https://news.ycombinator.com/item?id=48777266)

**Background**: Vladimir Kramnik, a former world chess champion, had publicly accused several top players of cheating in online tournaments based on his own statistical analyses, which many experts considered flawed. His allegations led to significant backlash and personal attacks against the accused players, with some suffering reputational damage and emotional distress.

**Discussion**: The community largely supports the sanction, with many expressing relief and criticizing Kramnik's actions as harmful. Some commenters note that the response from FIDE was too little, too late, and call for broader accountability regarding other controversial incidents in chess, such as the Hans Niemann saga.

**Tags**: `#chess`, `#ethics`, `#controversy`, `#sports`

---

<a id="item-13"></a>
## [Let AI coding assistants use their own judgment](https://simonwillison.net/2026/Jul/3/judgement/#atom-everything) ⭐️ 6.0/10

At an AI engineer fireside chat, the Claude Code team suggested letting AI coding assistants like Fable use their own judgment for tasks such as testing and model selection, rather than dictating explicit rules. Simon Willison also shared a tip to tell Claude Code to delegate coding tasks to lower-power models via subagents to save tokens. This approach can significantly improve developer productivity and reduce costs by allowing AI assistants to optimize their own workflows. As AI coding tools become more capable, trusting them with autonomy may become a key best practice. Simon Willison prompted Claude Code with a memory instruction to delegate coding tasks to subagents using lower-power models (Sonnet for substantive work, Haiku for trivial edits), while keeping judgment-heavy tasks in the main model. He reported getting more work done while consuming fewer Fable tokens.

rss · Simon Willison · Jul 3, 18:51

**Background**: Claude Code is an AI coding assistant built on Anthropic's Claude models, which include tiers like Haiku, Sonnet, and Opus. Fable is a newer, more powerful model (Claude Mythos) designed for complex tasks. The tip leverages the ability to spawn subagents with different models to balance cost and capability.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Claude_Code">Claude Code</a></li>
<li><a href="https://www.anthropic.com/claude/fable">Claude Fable \ Anthropic</a></li>

</ul>
</details>

**Tags**: `#AI coding assistants`, `#Claude Code`, `#prompt engineering`, `#developer productivity`

---