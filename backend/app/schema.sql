CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, deadline TEXT NOT NULL,
  team_size INTEGER NOT NULL, topic_desc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT (datetime('now')));

CREATE TABLE IF NOT EXISTS milestones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, order_idx INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned',
  expected_artifact_type TEXT NOT NULL,
  UNIQUE(project_id, order_idx));

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL, description TEXT,
  priority TEXT NOT NULL DEFAULT 'optional',
  difficulty TEXT NOT NULL DEFAULT 'mid',
  est_effort_days REAL NOT NULL DEFAULT 1.0,
  status TEXT NOT NULL DEFAULT 'planned',
  start_date TEXT, due_date TEXT, completed_at TEXT);

CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  note TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));

CREATE TABLE IF NOT EXISTS validation_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, file_type TEXT NOT NULL,
  result TEXT NOT NULL, fail_reasons TEXT,
  llm_used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')));

CREATE TABLE IF NOT EXISTS replan_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  gap_days REAL NOT NULL, proposal TEXT,
  applied INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')));

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  type TEXT NOT NULL, content TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'sent',
  response TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
