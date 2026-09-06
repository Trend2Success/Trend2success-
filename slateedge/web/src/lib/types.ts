export interface PlayerRow {
  id: string;
  playerId: string;
  name: string;
  team: string;
  opponent: string;
  position: string;
  gameInfo: string;
  salary: number;
  status: string;
  locked: boolean;
  excluded: boolean;
  notes: string;
  tags: { tag: string; label: string | null }[];
  projection: number | null;
  floor: number | null;
  ceiling: number | null;
  stdev: number | null;
  ownership: number | null;
  leverage: number | null;
  value: number | null;
  ceilingValue: number | null;
  chalkFlag: boolean;
  contrarianFlag: boolean;
}
