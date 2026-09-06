-- CreateEnum
CREATE TYPE "TagName" AS ENUM ('CORE', 'STRONG_PLAY', 'TOURNAMENT_PIVOT', 'VALUE', 'FADE', 'INJURY_WATCH', 'CUSTOM');

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "displayName" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "settings" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "sessionBudgetCents" INTEGER NOT NULL DEFAULT 10000,
    "stopLossCents" INTEGER NOT NULL DEFAULT 5000,
    "chalkThresholdPct" DOUBLE PRECISION NOT NULL DEFAULT 25,
    "contrarianOwnershipPct" DOUBLE PRECISION NOT NULL DEFAULT 8,
    "contrarianCeilingPctile" DOUBLE PRECISION NOT NULL DEFAULT 70,
    "defaultSalaryCap" INTEGER NOT NULL DEFAULT 50000,
    "featureFlags" JSONB NOT NULL DEFAULT '{}',
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "settings_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_logs" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "entityType" TEXT,
    "entityId" TEXT,
    "detail" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "slates" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "slateId" TEXT NOT NULL,
    "slateName" TEXT NOT NULL,
    "sport" TEXT NOT NULL DEFAULT 'NFL',
    "contestDate" TIMESTAMP(3) NOT NULL,
    "isDemo" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "slates_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "import_batches" (
    "id" TEXT NOT NULL,
    "slateId" TEXT NOT NULL,
    "kind" TEXT NOT NULL,
    "sourceLabel" TEXT NOT NULL,
    "fileName" TEXT,
    "rowCount" INTEGER NOT NULL,
    "errorCount" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "import_batches_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "players" (
    "id" TEXT NOT NULL,
    "slateId" TEXT NOT NULL,
    "playerId" TEXT NOT NULL,
    "playerName" TEXT NOT NULL,
    "team" TEXT NOT NULL,
    "opponent" TEXT NOT NULL,
    "position" TEXT NOT NULL,
    "rosterPositions" TEXT NOT NULL,
    "salary" INTEGER NOT NULL,
    "gameInfo" TEXT,
    "gameId" TEXT NOT NULL,
    "startTime" TIMESTAMP(3),
    "status" TEXT NOT NULL DEFAULT 'ACTIVE',
    "locked" BOOLEAN NOT NULL DEFAULT false,
    "excluded" BOOLEAN NOT NULL DEFAULT false,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "players_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "player_tags" (
    "id" TEXT NOT NULL,
    "playerId" TEXT NOT NULL,
    "tag" "TagName" NOT NULL,
    "label" TEXT,

    CONSTRAINT "player_tags_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "projection_sources" (
    "id" TEXT NOT NULL,
    "slateId" TEXT NOT NULL,
    "sourceLabel" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "projection_sources_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "projection_rows" (
    "id" TEXT NOT NULL,
    "sourceId" TEXT NOT NULL,
    "playerId" TEXT NOT NULL,
    "playerName" TEXT NOT NULL,
    "projectedPoints" DOUBLE PRECISION NOT NULL,
    "floor" DOUBLE PRECISION,
    "ceiling" DOUBLE PRECISION,
    "standardDeviation" DOUBLE PRECISION,
    "projectedOwnership" DOUBLE PRECISION,
    "expectedUsage" DOUBLE PRECISION,
    "targetShareOrUsage" DOUBLE PRECISION,
    "notes" TEXT,
    "lastUpdated" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "projection_rows_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "projection_snapshots" (
    "id" TEXT NOT NULL,
    "playerId" TEXT NOT NULL,
    "basePoints" DOUBLE PRECISION NOT NULL,
    "finalPoints" DOUBLE PRECISION NOT NULL,
    "floor" DOUBLE PRECISION,
    "ceiling" DOUBLE PRECISION,
    "standardDeviation" DOUBLE PRECISION,
    "projectedOwnership" DOUBLE PRECISION,
    "value" DOUBLE PRECISION,
    "ceilingValue" DOUBLE PRECISION,
    "leverageScore" DOUBLE PRECISION,
    "chalkFlag" BOOLEAN NOT NULL DEFAULT false,
    "contrarianFlag" BOOLEAN NOT NULL DEFAULT false,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "projection_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "projection_adjustments" (
    "id" TEXT NOT NULL,
    "playerId" TEXT NOT NULL,
    "editorUserId" TEXT NOT NULL,
    "kind" TEXT NOT NULL,
    "beforeValue" DOUBLE PRECISION NOT NULL,
    "afterValue" DOUBLE PRECISION NOT NULL,
    "detail" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "projection_adjustments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lineup_runs" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "slateId" TEXT NOT NULL,
    "presetName" TEXT NOT NULL DEFAULT 'Custom',
    "settingsJson" JSONB NOT NULL,
    "settingsVersion" TEXT NOT NULL DEFAULT '1.0',
    "seedUsed" INTEGER,
    "warnings" JSONB NOT NULL DEFAULT '[]',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "lineup_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lineups" (
    "id" TEXT NOT NULL,
    "runId" TEXT NOT NULL,
    "externalLineupId" TEXT NOT NULL,
    "salaryUsed" INTEGER NOT NULL,
    "totalProjection" DOUBLE PRECISION NOT NULL,
    "totalCeiling" DOUBLE PRECISION NOT NULL,
    "totalOwnership" DOUBLE PRECISION NOT NULL,
    "leverageScore" DOUBLE PRECISION NOT NULL,
    "modelScore" DOUBLE PRECISION NOT NULL,
    "stackSummary" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "lineups_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lineup_players" (
    "id" TEXT NOT NULL,
    "lineupId" TEXT NOT NULL,
    "playerId" TEXT NOT NULL,
    "slot" TEXT NOT NULL,

    CONSTRAINT "lineup_players_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "simulation_runs" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "slateId" TEXT NOT NULL,
    "distribution" TEXT NOT NULL,
    "numSimulations" INTEGER NOT NULL,
    "settingsJson" JSONB NOT NULL,
    "resultsJson" JSONB NOT NULL,
    "seedUsed" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "simulation_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "contest_results" (
    "id" TEXT NOT NULL,
    "slateId" TEXT NOT NULL,
    "contestName" TEXT NOT NULL,
    "contestType" TEXT NOT NULL,
    "fieldSize" INTEGER,
    "entryFeeCents" INTEGER NOT NULL,
    "numberOfEntries" INTEGER NOT NULL,
    "totalEntryFeesCents" INTEGER NOT NULL,
    "totalWinningsCents" INTEGER NOT NULL,
    "netProfitLossCents" INTEGER NOT NULL,
    "externalLineupRef" TEXT,
    "linkedLineupId" TEXT,
    "finalRank" INTEGER,
    "lineupPoints" DOUBLE PRECISION,
    "cashLine" DOUBLE PRECISION,
    "topOnePercentLine" DOUBLE PRECISION,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "contest_results_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "settings_userId_key" ON "settings"("userId");

-- CreateIndex
CREATE INDEX "audit_logs_userId_createdAt_idx" ON "audit_logs"("userId", "createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "slates_userId_slateId_key" ON "slates"("userId", "slateId");

-- CreateIndex
CREATE INDEX "players_slateId_position_idx" ON "players"("slateId", "position");

-- CreateIndex
CREATE UNIQUE INDEX "players_slateId_playerId_key" ON "players"("slateId", "playerId");

-- CreateIndex
CREATE UNIQUE INDEX "player_tags_playerId_tag_label_key" ON "player_tags"("playerId", "tag", "label");

-- CreateIndex
CREATE UNIQUE INDEX "projection_sources_slateId_sourceLabel_key" ON "projection_sources"("slateId", "sourceLabel");

-- CreateIndex
CREATE UNIQUE INDEX "projection_rows_sourceId_playerId_key" ON "projection_rows"("sourceId", "playerId");

-- CreateIndex
CREATE UNIQUE INDEX "projection_snapshots_playerId_key" ON "projection_snapshots"("playerId");

-- CreateIndex
CREATE INDEX "projection_adjustments_playerId_createdAt_idx" ON "projection_adjustments"("playerId", "createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "lineup_players_lineupId_playerId_key" ON "lineup_players"("lineupId", "playerId");

-- CreateIndex
CREATE UNIQUE INDEX "contest_results_linkedLineupId_key" ON "contest_results"("linkedLineupId");

-- AddForeignKey
ALTER TABLE "settings" ADD CONSTRAINT "settings_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "slates" ADD CONSTRAINT "slates_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "import_batches" ADD CONSTRAINT "import_batches_slateId_fkey" FOREIGN KEY ("slateId") REFERENCES "slates"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "players" ADD CONSTRAINT "players_slateId_fkey" FOREIGN KEY ("slateId") REFERENCES "slates"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "player_tags" ADD CONSTRAINT "player_tags_playerId_fkey" FOREIGN KEY ("playerId") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "projection_rows" ADD CONSTRAINT "projection_rows_sourceId_fkey" FOREIGN KEY ("sourceId") REFERENCES "projection_sources"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "projection_snapshots" ADD CONSTRAINT "projection_snapshots_playerId_fkey" FOREIGN KEY ("playerId") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "projection_adjustments" ADD CONSTRAINT "projection_adjustments_playerId_fkey" FOREIGN KEY ("playerId") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "projection_adjustments" ADD CONSTRAINT "projection_adjustments_editorUserId_fkey" FOREIGN KEY ("editorUserId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_runs" ADD CONSTRAINT "lineup_runs_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_runs" ADD CONSTRAINT "lineup_runs_slateId_fkey" FOREIGN KEY ("slateId") REFERENCES "slates"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineups" ADD CONSTRAINT "lineups_runId_fkey" FOREIGN KEY ("runId") REFERENCES "lineup_runs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_players" ADD CONSTRAINT "lineup_players_lineupId_fkey" FOREIGN KEY ("lineupId") REFERENCES "lineups"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lineup_players" ADD CONSTRAINT "lineup_players_playerId_fkey" FOREIGN KEY ("playerId") REFERENCES "players"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "simulation_runs" ADD CONSTRAINT "simulation_runs_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "simulation_runs" ADD CONSTRAINT "simulation_runs_slateId_fkey" FOREIGN KEY ("slateId") REFERENCES "slates"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contest_results" ADD CONSTRAINT "contest_results_slateId_fkey" FOREIGN KEY ("slateId") REFERENCES "slates"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contest_results" ADD CONSTRAINT "contest_results_linkedLineupId_fkey" FOREIGN KEY ("linkedLineupId") REFERENCES "lineups"("id") ON DELETE SET NULL ON UPDATE CASCADE;
