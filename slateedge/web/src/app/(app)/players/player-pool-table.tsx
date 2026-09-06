'use client';

import { useMemo, useState } from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input, Label } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import type { PlayerRow } from '@/lib/types';
import { LockExcludeButtons, NotesDialog, TagsDialog } from './player-row-actions';

function StatusBadge({ status }: { status: string }) {
  if (status === 'OUT') return <Badge variant="rose">Out</Badge>;
  if (status === 'QUESTIONABLE') return <Badge variant="amber">Questionable</Badge>;
  return <Badge variant="outline">Active</Badge>;
}

export function PlayerPoolTable({ rows }: { rows: PlayerRow[] }) {
  const [globalFilter, setGlobalFilter] = useState('');
  const [position, setPosition] = useState('ALL');
  const [team, setTeam] = useState('ALL');
  const [game, setGame] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [excludedOnly, setExcludedOnly] = useState(false);
  const [salaryMin, setSalaryMin] = useState('');
  const [salaryMax, setSalaryMax] = useState('');
  const [projMin, setProjMin] = useState('');
  const [projMax, setProjMax] = useState('');
  const [ownMin, setOwnMin] = useState('');
  const [ownMax, setOwnMax] = useState('');

  const teams = useMemo(() => [...new Set(rows.map((r) => r.team))].sort(), [rows]);
  const games = useMemo(() => [...new Set(rows.map((r) => r.gameInfo))].sort(), [rows]);

  const filteredRows = useMemo(() => {
    return rows.filter((r) => {
      if (position !== 'ALL' && r.position !== position) return false;
      if (team !== 'ALL' && r.team !== team) return false;
      if (game !== 'ALL' && r.gameInfo !== game) return false;
      if (status !== 'ALL' && r.status !== status) return false;
      if (excludedOnly && !r.excluded) return false;
      if (globalFilter && !r.name.toLowerCase().includes(globalFilter.toLowerCase())) return false;
      if (salaryMin && r.salary < Number(salaryMin)) return false;
      if (salaryMax && r.salary > Number(salaryMax)) return false;
      if (projMin && (r.projection ?? -Infinity) < Number(projMin)) return false;
      if (projMax && (r.projection ?? Infinity) > Number(projMax)) return false;
      if (ownMin && (r.ownership ?? -Infinity) < Number(ownMin)) return false;
      if (ownMax && (r.ownership ?? Infinity) > Number(ownMax)) return false;
      return true;
    });
  }, [rows, position, team, game, status, excludedOnly, globalFilter, salaryMin, salaryMax, projMin, projMax, ownMin, ownMax]);

  const columns = useMemo<ColumnDef<PlayerRow>[]>(
    () => [
      {
        accessorKey: 'name',
        header: 'Player',
        cell: ({ row }) => (
          <div>
            <p className="font-medium text-ink-50">{row.original.name}</p>
            <p className="text-[11px] text-ink-400">
              {row.original.team} vs {row.original.opponent} · {row.original.position}
            </p>
          </div>
        ),
      },
      { accessorKey: 'salary', header: 'Salary', cell: ({ getValue }) => `$${(getValue() as number).toLocaleString()}` },
      { accessorKey: 'projection', header: 'Proj', cell: ({ getValue }) => fmt(getValue()) },
      { accessorKey: 'floor', header: 'Floor', cell: ({ getValue }) => fmt(getValue()) },
      { accessorKey: 'ceiling', header: 'Ceiling', cell: ({ getValue }) => fmt(getValue()) },
      { accessorKey: 'stdev', header: 'StdDev', cell: ({ getValue }) => fmt(getValue()) },
      { accessorKey: 'ownership', header: 'Own%', cell: ({ getValue }) => fmt(getValue(), '%') },
      {
        accessorKey: 'leverage',
        header: 'Leverage',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            {fmt(row.original.leverage)}
            {row.original.chalkFlag ? <Badge variant="amber">Chalk</Badge> : null}
            {row.original.contrarianFlag ? <Badge variant="teal">Contrarian</Badge> : null}
          </div>
        ),
      },
      { accessorKey: 'value', header: 'Value', cell: ({ getValue }) => fmt(getValue()) },
      { accessorKey: 'ceilingValue', header: 'Ceil Value', cell: ({ getValue }) => fmt(getValue()) },
      { accessorKey: 'status', header: 'Status', cell: ({ getValue }) => <StatusBadge status={getValue() as string} /> },
      {
        id: 'tags',
        header: 'Tags',
        cell: ({ row }) => <TagsDialog playerId={row.original.id} tags={row.original.tags} />,
      },
      {
        id: 'actions',
        header: 'Manage',
        cell: ({ row }) => (
          <div className="flex items-center gap-1">
            <LockExcludeButtons playerId={row.original.id} locked={row.original.locked} excluded={row.original.excluded} />
            <NotesDialog playerId={row.original.id} notes={row.original.notes} />
          </div>
        ),
      },
    ],
    []
  );

  const table = useReactTable({
    data: filteredRows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
        <Input placeholder="Search name…" value={globalFilter} onChange={(e) => setGlobalFilter(e.target.value)} />
        <FilterSelect label="Position" value={position} onChange={setPosition} options={['ALL', 'QB', 'RB', 'WR', 'TE', 'DST']} />
        <FilterSelect label="Team" value={team} onChange={setTeam} options={['ALL', ...teams]} />
        <FilterSelect label="Game" value={game} onChange={setGame} options={['ALL', ...games]} />
        <FilterSelect label="Status" value={status} onChange={setStatus} options={['ALL', 'ACTIVE', 'QUESTIONABLE', 'OUT']} />
        <label className="flex items-center gap-2 self-end pb-1 text-xs text-ink-200">
          <Checkbox checked={excludedOnly} onCheckedChange={(v) => setExcludedOnly(v === true)} />
          Excluded only
        </label>
        <RangeFilter label="Salary" min={salaryMin} max={salaryMax} setMin={setSalaryMin} setMax={setSalaryMax} />
        <RangeFilter label="Projection" min={projMin} max={projMax} setMin={setProjMin} setMax={setProjMax} />
        <RangeFilter label="Ownership %" min={ownMin} max={ownMax} setMin={setOwnMin} setMax={setOwnMax} />
      </div>

      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id}>
              {hg.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className="cursor-pointer select-none"
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <span className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getCanSort() ? (
                      header.column.getIsSorted() === 'asc' ? (
                        <ArrowUp className="h-3 w-3" />
                      ) : header.column.getIsSorted() === 'desc' ? (
                        <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )
                    ) : null}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id} className={row.original.excluded ? 'opacity-50' : undefined}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
              ))}
            </TableRow>
          ))}
          {table.getRowModel().rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="py-8 text-center text-ink-400">
                No players match these filters.
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between text-xs text-ink-400">
        <span>
          {filteredRows.length} of {rows.length} players
        </span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
            Prev
          </Button>
          <span>
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount() || 1}
          </span>
          <Button size="sm" variant="outline" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

function fmt(v: unknown, suffix = ''): string {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toFixed(1)}${suffix}`;
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="sr-only">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder={label} />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o === 'ALL' ? `All ${label.toLowerCase()}s` : o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function RangeFilter({
  label,
  min,
  max,
  setMin,
  setMax,
}: {
  label: string;
  min: string;
  max: string;
  setMin: (v: string) => void;
  setMax: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-[10px]">{label}</Label>
      <div className="flex gap-1">
        <Input placeholder="Min" value={min} onChange={(e) => setMin(e.target.value)} className="h-8" />
        <Input placeholder="Max" value={max} onChange={(e) => setMax(e.target.value)} className="h-8" />
      </div>
    </div>
  );
}
