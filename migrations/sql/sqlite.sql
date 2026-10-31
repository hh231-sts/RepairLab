CREATE TABLE budget_pool (
	id VARCHAR(24) NOT NULL, 
	limit_cny FLOAT NOT NULL, 
	spent FLOAT NOT NULL, 
	reserved FLOAT NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE experiments (
	id VARCHAR(32) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	config JSON NOT NULL, 
	formal BOOLEAN NOT NULL, 
	launched BOOLEAN NOT NULL, 
	memory_snapshot JSON NOT NULL, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE projects (
	id VARCHAR(32) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	repository TEXT NOT NULL, 
	"commit" VARCHAR(100) NOT NULL, 
	snapshot_hash VARCHAR(64) NOT NULL, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE skills (
	id VARCHAR(100) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	version INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE documents (
	id VARCHAR(64) NOT NULL, 
	project_id VARCHAR(32) NOT NULL, 
	"commit" VARCHAR(100) NOT NULL, 
	source_version VARCHAR(100) NOT NULL, 
	origin VARCHAR(24) NOT NULL, 
	path TEXT NOT NULL, 
	line INTEGER NOT NULL, 
	symbol VARCHAR(200), 
	content TEXT NOT NULL, 
	vector JSON, 
	vector_source VARCHAR(80), 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);

CREATE INDEX ix_documents_project_id ON documents (project_id);

CREATE TABLE issues (
	id VARCHAR(32) NOT NULL, 
	project_id VARCHAR(32) NOT NULL, 
	contract JSON NOT NULL, 
	contract_hash VARCHAR(64) NOT NULL, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);

CREATE TABLE memories (
	id VARCHAR(32) NOT NULL, 
	project_id VARCHAR(32) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	entry JSON NOT NULL, 
	validation JSON NOT NULL, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);

CREATE INDEX ix_memories_project_id ON memories (project_id);

CREATE TABLE runs (
	id VARCHAR(32) NOT NULL, 
	issue_id VARCHAR(32) NOT NULL, 
	submission_key VARCHAR(100), 
	retry_of VARCHAR(32), 
	experiment_id VARCHAR(32), 
	status VARCHAR(24) NOT NULL, 
	control VARCHAR(16), 
	terminal_reason TEXT, 
	model_source VARCHAR(24) NOT NULL, 
	strategy VARCHAR(24) NOT NULL, 
	script VARCHAR(100) NOT NULL, 
	owner VARCHAR(100), 
	epoch INTEGER NOT NULL, 
	lease_until FLOAT NOT NULL, 
	started_at FLOAT, 
	created_at FLOAT NOT NULL, 
	ended_at FLOAT, 
	calls INTEGER NOT NULL, 
	spent FLOAT NOT NULL, 
	reserved FLOAT NOT NULL, 
	patch_hash VARCHAR(64), 
	versions JSON NOT NULL, 
	memory_snapshot JSON NOT NULL, 
	event_seq INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES issues (id), 
	UNIQUE (submission_key)
);

CREATE INDEX ix_runs_experiment_id ON runs (experiment_id);

CREATE INDEX ix_runs_status ON runs (status);

CREATE TABLE agents (
	id VARCHAR(80) NOT NULL, 
	run_id VARCHAR(32) NOT NULL, 
	parent_id VARCHAR(80), 
	"key" VARCHAR(40) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	request JSON NOT NULL, 
	cursor INTEGER NOT NULL, 
	messages JSON NOT NULL, 
	pending JSON, 
	artifacts JSON NOT NULL, 
	summary TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
);

CREATE INDEX ix_agents_run_id ON agents (run_id);

CREATE TABLE artifacts (
	id VARCHAR(32) NOT NULL, 
	run_id VARCHAR(32) NOT NULL, 
	agent_id VARCHAR(80) NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size INTEGER NOT NULL, 
	metadata_json JSON NOT NULL, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
);

CREATE INDEX ix_artifacts_run_id ON artifacts (run_id);

CREATE TABLE events (
	id INTEGER NOT NULL, 
	run_id VARCHAR(32) NOT NULL, 
	seq INTEGER NOT NULL, 
	kind VARCHAR(80) NOT NULL, 
	payload JSON NOT NULL, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
);

CREATE UNIQUE INDEX event_run_seq ON events (run_id, seq);

CREATE INDEX ix_events_run_id ON events (run_id);

CREATE TABLE model_calls (
	id VARCHAR(80) NOT NULL, 
	run_id VARCHAR(32) NOT NULL, 
	source VARCHAR(24) NOT NULL, 
	reserved FLOAT NOT NULL, 
	actual FLOAT, 
	status VARCHAR(24) NOT NULL, 
	metadata_json JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
);

CREATE INDEX ix_model_calls_run_id ON model_calls (run_id);

CREATE TABLE verifications (
	id VARCHAR(32) NOT NULL, 
	run_id VARCHAR(32) NOT NULL, 
	patch_hash VARCHAR(64) NOT NULL, 
	snapshot_hash VARCHAR(64) NOT NULL, 
	environment_hash VARCHAR(100) NOT NULL, 
	verifier_hash VARCHAR(64) NOT NULL, 
	passed BOOLEAN NOT NULL, 
	reason TEXT NOT NULL, 
	artifact_id VARCHAR(32) NOT NULL, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
);

CREATE INDEX ix_verifications_run_id ON verifications (run_id);

CREATE TABLE receipts (
	id VARCHAR(64) NOT NULL, 
	run_id VARCHAR(32) NOT NULL, 
	agent_id VARCHAR(80) NOT NULL, 
	epoch INTEGER NOT NULL, 
	name VARCHAR(60) NOT NULL, 
	arguments JSON NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	"plan" JSON NOT NULL, 
	result JSON, 
	created_at FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
);

CREATE INDEX ix_receipts_run_id ON receipts (run_id);
