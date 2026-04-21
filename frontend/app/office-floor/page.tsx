<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Office Floor — Stock To Me Edition</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            min-height: 100vh;
            overflow: auto;
            color: #333;
        }

        .office-container {
            width: 1400px;
            min-height: 1000px;
            margin: 20px auto;
            background: linear-gradient(180deg, #2d2d44 0%, #1a1a2e 100%);
            position: relative;
            border-radius: 8px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            border: 2px solid #3a3a5a;
        }

        .office-container::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image:
                linear-gradient(90deg, rgba(0,255,136,0.05) 1px, transparent 1px),
                linear-gradient(rgba(0,255,136,0.05) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
        }

        .office-title {
            position: absolute;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 1.5rem;
            color: #00ff88;
            text-transform: uppercase;
            letter-spacing: 4px;
            text-shadow: 0 0 10px rgba(0,255,136,0.5);
        }

        .zone-label {
            position: absolute;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 600;
        }

        .zone-dev   { top: 80px;  left: 100px; color: #00ffff; }
        .zone-research  { top: 80px;  right: 100px; color: #00ffff; }
        .zone-ops   { bottom: 150px; left: 100px; color: #ffaa00; }
        .zone-trading { bottom: 150px; right: 100px; color: #ff6688; }
        .zone-mgmt  { top: 50%; left: 50%; transform: translate(-50%, -50%); }

        .desk {
            position: absolute;
            width: 140px;
            height: 100px;
            background: linear-gradient(145deg, #4a4a6a 0%, #3a3a5a 100%);
            border-radius: 4px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1);
            cursor: pointer;
            transition: all 0.3s ease;
            border: 1px solid #5a5a7a;
        }

        .desk:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.6), 0 0 20px rgba(0,255,136,0.2);
            border-color: #00ff88;
        }

        .desk::before {
            content: '';
            position: absolute;
            top: 10px; left: 10px; right: 10px;
            height: 4px;
            background: rgba(0,0,0,0.3);
            border-radius: 2px;
        }

        /* Desk positions — Development (NW) */
        .desk-alex   { top: 120px; left: 80px; }
        .desk-jordan { top: 120px; left: 240px; }

        /* Desk positions — Research (NE) */
        .desk-sam    { top: 120px; right: 240px; }
        .desk-taylor { top: 120px; right: 80px; }

        /* Desk positions — Operations (SW) */
        .desk-morgan { bottom: 150px; left: 80px; }
        .desk-casey  { bottom: 150px; left: 240px; }

        /* Desk positions — Trading (SE) */
        .desk-broker { bottom: 150px; right: 80px; width: 160px; }

        /* Agent base */
        .agent {
            position: absolute;
            width: 40px;
            height: 40px;
            cursor: pointer;
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 100;
        }

        .agent svg {
            width: 100%; height: 100%;
            filter: drop-shadow(0 0 8px currentColor);
        }

        .agent:hover { transform: scale(1.2); }
        .agent-moving { z-index: 200; }

        .status-active { color: #00ff88; }
        .status-idle  { color: #ffaa00; }
        .status-busy  { color: #ff4444; }

        /* Agent positions at desks */
        .agent-alex   { top: 165px; left: 130px; }
        .agent-jordan { top: 165px; left: 290px; }
        .agent-sam    { top: 165px; right: 290px; }
        .agent-taylor { top: 165px; right: 130px; }
        .agent-morgan { bottom: 220px; left: 130px; }
        .agent-casey  { bottom: 220px; left: 290px; }
        .agent-riley  { top: 20px; left: 50%; transform: translateX(-50%); }
        .agent-broker { bottom: 220px; right: 130px; }

        /* Labels */
        .agent-label {
            position: absolute;
            font-size: 0.75rem;
            font-weight: 600;
            color: #ccc;
            background: rgba(0,0,0,0.7);
            padding: 2px 8px;
            border-radius: 10px;
            white-space: nowrap;
            border: 1px solid #444;
        }

        .label-alex   { top: 210px; left: 115px; }
        .label-jordan { top: 210px; left: 275px; }
        .label-sam    { top: 210px; right: 275px; }
        .label-taylor { top: 210px; right: 115px; }
        .label-morgan { bottom: 175px; left: 115px; }
        .label-casey  { bottom: 175px; left: 275px; }
        .label-riley  { top: 65px; left: 50%; transform: translateX(-50%); }
        .label-broker { bottom: 175px; right: 115px; color: #ff6688; border-color: #ff6688; }

        /* Meeting Table (center) */
        .meeting-area {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
        }

        .meeting-table {
            width: 300px;
            height: 180px;
            background: linear-gradient(145deg, #3a3a5a 0%, #2a2a4a 100%);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5), inset 0 2px 0 rgba(255,255,255,0.1), 0 0 30px rgba(0,255,136,0.1);
            position: relative;
            border: 2px solid #4a4a6a;
        }

        .meeting-table::before {
            content: 'CONFERENCE';
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            font-size: 0.8rem;
            letter-spacing: 3px;
            color: rgba(0,255,136,0.3);
        }

        .chair {
            position: absolute;
            width: 40px; height: 40px;
            background: #444;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }

        .chair-n { top: -25px; left: 50%; transform: translateX(-50%); }
        .chair-s { bottom: -25px; left: 50%; transform: translateX(-50%); }
        .chair-e { right: -25px; top: 50%; transform: translateY(-50%); }
        .chair-w { left: -25px; top: 50%; transform: translateY(-50%); }

        /* Info Panel */
        .info-panel {
            position: fixed;
            top: 20px; right: 20px;
            width: 320px;
            background: rgba(20,20,35,0.97);
            border-radius: 12px;
            padding: 20px;
            color: #e0e0e0;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            max-height: 80vh;
            overflow-y: auto;
            border: 1px solid #3a3a5a;
            z-index: 1000;
        }

        .info-panel h3 {
            margin-bottom: 15px;
            color: #00ff88;
            font-size: 1.1rem;
            text-shadow: 0 0 10px rgba(0,255,136,0.3);
        }

        .info-section {
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .info-section:last-child { border-bottom: none; }

        .info-section h4 {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 8px;
        }

        .info-section p, .info-section li {
            font-size: 0.9rem;
            line-height: 1.5;
            color: #ccc;
        }

        .info-section ul { list-style: none; padding-left: 0; }
        .info-section li::before { content: '• '; color: #00ff88; }

        .close-btn {
            position: absolute;
            top: 10px; right: 10px;
            background: none; border: none;
            color: #888;
            font-size: 1.2rem;
            cursor: pointer;
        }

        .close-btn:hover { color: #fff; }

        /* Collaboration line */
        .collab-path {
            position: absolute;
            pointer-events: none;
            z-index: 50;
        }

        .collab-line {
            stroke: #00ff88;
            stroke-width: 2;
            fill: none;
            stroke-dasharray: 5,5;
            opacity: 0;
            transition: opacity 0.3s;
        }

        .collab-active .collab-line {
            opacity: 0.6;
            animation: dash 1s linear infinite;
        }

        @keyframes dash {
            to { stroke-dashoffset: -10; }
        }

        /* Legend */
        .legend {
            position: absolute;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            padding: 15px;
            border-radius: 8px;
            font-size: 0.8rem;
            border: 1px solid #3a3a5a;
        }

        .legend h4 { margin-bottom: 10px; color: #00ff88; }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 5px;
            color: #ccc;
        }

        .legend-dot {
            width: 10px; height: 10px;
            border-radius: 50%;
        }

        /* Control Panel */
        .control-panel {
            position: fixed;
            bottom: 20px; left: 20px;
            background: rgba(20,20,35,0.95);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #3a3a5a;
            color: #ccc;
            z-index: 1000;
        }

        .control-panel h4 { color: #00ff88; margin-bottom: 10px; }

        .control-btn {
            background: #3a3a5a;
            border: 1px solid #4a4a6a;
            color: #ccc;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .control-btn:hover {
            background: #4a4a6a;
            border-color: #00ff88;
            color: #00ff88;
        }

        /* Broker collaboration styles */
        .broker-collab .collab-line {
            stroke: #ff6688;
        }

        .broker-collab-active .collab-line {
            opacity: 0.6;
            animation: dashPink 1s linear infinite;
        }

        @keyframes dashPink {
            to { stroke-dashoffset: -10; }
        }
    </style>
</head>
<body>
    <svg class="collab-path" width="1400" height="1000">
        <path class="collab-line" id="collabPath" d="" />
    </svg>

    <div class="office-container" id="office">
        <div class="office-title">🏢 Agent Headquarters — Stock To Me Edition</div>

        <!-- Zone Labels -->
        <div class="zone-label zone-dev">Development</div>
        <div class="zone-label zone-research">Research</div>
        <div class="zone-label zone-ops">Operations</div>
        <div class="zone-label zone-trading">Trading</div>

        <!-- ── Development ── -->
        <div class="desk desk-alex"   onclick="showAgentInfo('alex')"></div>
        <div class="agent agent-alex status-active" id="agent-alex" onclick="showAgentInfo('alex')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-alex">Alex (Dev)</div>

        <div class="desk desk-jordan" onclick="showAgentInfo('jordan')"></div>
        <div class="agent agent-jordan status-active" id="agent-jordan" onclick="showAgentInfo('jordan')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-jordan">Jordan (QA)</div>

        <!-- ── Research ── -->
        <div class="desk desk-sam"    onclick="showAgentInfo('sam')"></div>
        <div class="agent agent-sam status-active" id="agent-sam" onclick="showAgentInfo('sam')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-sam">Sam (Research)</div>

        <div class="desk desk-taylor" onclick="showAgentInfo('taylor')"></div>
        <div class="agent agent-taylor status-idle" id="agent-taylor" onclick="showAgentInfo('taylor')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-taylor">Taylor (Data)</div>

        <!-- ── Operations ── -->
        <div class="desk desk-morgan" onclick="showAgentInfo('morgan')"></div>
        <div class="agent agent-morgan status-idle" id="agent-morgan" onclick="showAgentInfo('morgan')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-morgan">Morgan (Track)</div>

        <div class="desk desk-casey"  onclick="showAgentInfo('casey')"></div>
        <div class="agent agent-casey status-active" id="agent-casey" onclick="showAgentInfo('casey')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-casey">Casey (Acct)</div>

        <!-- ── Trading (Broker) ── -->
        <div class="desk desk-broker" onclick="showAgentInfo('broker')"></div>
        <div class="agent agent-broker status-active" id="agent-broker" onclick="showAgentInfo('broker')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-broker">Broker (Trading)</div>

        <!-- ── PM Office ── -->
        <div class="meeting-area">
            <div class="meeting-table">
                <div class="chair chair-n"></div>
                <div class="chair chair-s"></div>
                <div class="chair chair-e"></div>
                <div class="chair chair-w"></div>
            </div>
        </div>

        <div class="agent agent-riley status-active" id="agent-riley" onclick="showAgentInfo('riley')">
            <svg viewBox="0 0 11 8"><path fill="currentColor" d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"/></svg>
        </div>
        <div class="agent-label label-riley">Riley (PM)</div>

        <!-- Legend -->
        <div class="legend">
            <h4>Status</h4>
            <div class="legend-item">
                <div class="legend-dot" style="background:#00ff88;box-shadow:0 0 8px #00ff88;"></div><span>Active</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#ffaa00;box-shadow:0 0 8px #ffaa00;"></div><span>Idle</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background:#ff4444;box-shadow:0 0 8px #ff4444;"></div><span>Busy</span>
            </div>
        </div>
    </div>

    <!-- Info Panel -->
    <div class="info-panel" id="infoPanel" style="display:none;">
        <button class="close-btn" onclick="closeInfo()">×</button>
        <div id="infoContent"></div>
    </div>

    <!-- Control Panel -->
    <div class="control-panel">
        <h4>🎮 Controls</h4>
        <button class="control-btn" onclick="simulatePairMeeting()">Pair Meeting</button>
        <button class="control-btn" onclick="simulateBrokerResearch()">Broker → Research</button>
        <button class="control-btn" onclick="simulateTeamMeeting()">Team Meeting</button>
        <button class="control-btn" onclick="returnToDesks()">All to Desks</button>
    </div>

    <script>
        const agents = {
            alex: {
                name: 'Alex', role: 'Senior Developer', department: 'Development',
                specialty: 'Full-stack coding, architecture', stack: 'Python, JS, FastAPI, Next.js',
                currentTask: 'Building Stock To Me dashboard', status: 'active',
                deskPos: { top: 165, left: 130 }
            },
            jordan: {
                name: 'Jordan', role: 'Code Reviewer', department: 'Development',
                specialty: 'PR reviews, testing, quality assurance', stack: 'Linting, CI/CD',
                currentTask: 'Reviewing SEC ingestion service', status: 'active',
                deskPos: { top: 165, left: 290 }
            },
            sam: {
                name: 'Sam', role: 'Research Lead', department: 'Research',
                specialty: 'Deep research, SEC filings, pattern analysis', stack: 'EDGAR, financial data',
                currentTask: 'Researching EDGAR API patterns for S-1 extraction', status: 'active',
                deskPos: { top: 165, right: 290 }
            },
            taylor: {
                name: 'Taylor', role: 'Data Analyst', department: 'Research',
                specialty: 'Data processing, visualization', stack: 'Pandas, SQL, Recharts',
                currentTask: 'Idle — awaiting data task', status: 'idle',
                deskPos: { top: 165, right: 130 }
            },
            morgan: {
                name: 'Morgan', role: 'Tracker', department: 'Operations',
                specialty: 'Task tracking, reminders, scheduling', stack: 'Calendar, todo systems',
                currentTask: 'Idle — monitoring systems', status: 'idle',
                deskPos: { bottom: 220, left: 130 }
            },
            casey: {
                name: 'Casey', role: 'Accountant', department: 'Operations',
                specialty: 'Expense tracking, budgeting', stack: 'Spreadsheets, receipts',
                currentTask: 'Setting up expense categories', status: 'active',
                deskPos: { bottom: 220, left: 290 }
            },
            riley: {
                name: 'Riley', role: 'Project Manager', department: 'Management',
                specialty: 'Coordination, planning, cross-team communication', stack: 'Project boards',
                currentTask: 'Coordinating Stock To Me build', status: 'active',
                deskPos: { top: 20, left: 50 }
            },
            broker: {
                name: 'Broker', role: 'Stock Broker', department: 'Trading',
                specialty: 'Small-cap opportunity identification, trap detection, dilution analysis',
                stack: 'Stock To Me platform, SEC EDGAR, market data',
                currentTask: 'Analyzing small-cap setups — looking for pump-before-offering patterns', status: 'active',
                deskPos: { bottom: 220, right: 130 }
            }
        };

        function showAgentInfo(agentId) {
            const agent = agents[agentId];
            const panel = document.getElementById('infoPanel');
            const content = document.getElementById('infoContent');

            // Broker gets special styling
            const isBroker = agentId === 'broker';
            const accentColor = isBroker ? '#ff6688' : '#00ff88';

            content.innerHTML = `
                <h3 style="color:${accentColor}">${agent.name} — ${agent.role}</h3>
                ${isBroker ? '<p style="color:#ff6688;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px">📈 Trading Department</p>' : ''}

                <div class="info-section">
                    <h4>Department</h4><p>${agent.department}</p>
                </div>
                <div class="info-section">
                    <h4>Specialty</h4><p>${agent.specialty}</p>
                </div>
                <div class="info-section">
                    <h4>Tech Stack</h4><p>${agent.stack}</p>
                </div>
                <div class="info-section">
                    <h4>Current Task</h4><p>${agent.currentTask}</p>
                </div>
                <div class="info-section">
                    <h4>Status</h4>
                    <p style="color:${getStatusColor(agent.status)};text-shadow:0 0 10px ${getStatusColor(agent.status)}">${agent.status.toUpperCase()}</p>
                </div>
                ${isBroker ? `
                <div class="info-section">
                    <h4>Broker Actions</h4>
                    <ul>
                        <li>Request research analysis from Sam + Taylor</li>
                        <li>Flag high trap-score names for review</li>
                        <li>Run dilution impact check on target names</li>
                        <li>Scan universe for financing setups</li>
                    </ul>
                </div>` : ''}
            `;

            panel.style.display = 'block';
        }

        function getStatusColor(status) {
            return { active: '#00ff88', idle: '#ffaa00', busy: '#ff4444' }[status] || '#ccc';
        }

        function closeInfo() {
            document.getElementById('infoPanel').style.display = 'none';
        }

        function moveAgent(agentId, targetPos, duration = 1000) {
            const agent = document.getElementById(`agent-${agentId}`);
            agent.classList.add('agent-moving');

            if (targetPos.top !== undefined) {
                agent.style.top = targetPos.top + 'px';
                agent.style.bottom = 'auto';
            }
            if (targetPos.bottom !== undefined) {
                agent.style.bottom = targetPos.bottom + 'px';
                agent.style.top = 'auto';
            }
            if (targetPos.left !== undefined) {
                agent.style.left = targetPos.left + 'px';
                agent.style.right = 'auto';
            }
            if (targetPos.right !== undefined) {
                agent.style.right = targetPos.right + 'px';
                agent.style.left = 'auto';
            }

            setTimeout(() => agent.classList.remove('agent-moving'), duration);
        }

        function drawCollabLine(x1, y1, x2, y2, color = '#00ff88') {
            const path = document.getElementById('collabPath');
            path.setAttribute('d', `M${x1},${y1} L${x2},${y2}`);
            path.setAttribute('stroke', color);
            document.body.classList.add('collab-active');
        }

        function clearCollabLine() {
            document.body.classList.remove('collab-active');
            document.getElementById('collabPath').setAttribute('d', '');
        }

        function returnToDesks() {
            Object.keys(agents).forEach(agentId => {
                moveAgent(agentId, agents[agentId].deskPos);
            });
            clearCollabLine();
        }

        function simulatePairMeeting() {
            moveAgent('alex', { top: 165, left: 260 });
            drawCollabLine(150, 185, 310, 185);
            setTimeout(() => { returnToDesks(); clearCollabLine(); }, 5000);
        }

        function simulateBrokerResearch() {
            // Broker moves toward Sam (Research collaboration)
            // Broker is at bottom-right, Sam is at top-right
            moveAgent('broker', { top: 165, right: 80 });
            moveAgent('sam', { top: 165, right: 200 });
            moveAgent('taylor', { top: 165, right: 320 });

            // Draw pink collaboration line from broker to sam
            drawCollabLine(1300, 185, 1150, 185, '#ff6688');

            // Update agent tasks
            agents.broker.currentTask = 'Collaborating with Research — analyzing trap scores';
            agents.sam.currentTask = 'Running pattern analysis for Broker';
            agents.taylor.currentTask = 'Pulling dilution data for Broker';

            setTimeout(() => {
                returnToDesks();
                clearCollabLine();
                agents.broker.currentTask = 'Analyzing small-cap setups';
                agents.sam.currentTask = 'Researching EDGAR API patterns';
                agents.taylor.currentTask = 'Idle — awaiting data task';
            }, 6000);
        }

        function simulateTeamMeeting() {
            const agentIds = ['alex', 'jordan', 'sam', 'casey'];
            const meetingPositions = [
                { top: 430, left: 540 },  // north
                { top: 500, left: 700 },  // east
                { top: 530, left: 540 },  // south
                { top: 500, left: 380 },  // west
            ];

            agentIds.forEach((id, i) => {
                setTimeout(() => moveAgent(id, meetingPositions[i]), i * 200);
            });

            // Riley joins from above
            setTimeout(() => moveAgent('riley', { top: 420, left: 660 }), 1000);

            setTimeout(() => returnToDesks(), 7000);
        }

        // Auto-demo: occasional Broker → Research pulses
        setInterval(() => {
            if (Math.random() > 0.7) {
                simulateBrokerResearch();
            }
        }, 20000);
    </script>
</body>
</html>
