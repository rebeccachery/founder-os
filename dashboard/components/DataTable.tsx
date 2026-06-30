interface Column<T> {
  key: keyof T | string;
  label: string;
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T extends object> {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
}

export function DataTable<T extends object>({
  columns,
  rows,
  emptyMessage = "No items yet. Run an agent to populate data.",
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-zinc-700 p-8 text-center text-zinc-400">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-zinc-800 bg-zinc-900 text-zinc-400">
          <tr>
            {columns.map((col) => (
              <th key={String(col.key)} className="px-4 py-3 font-medium">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-900/50">
              {columns.map((col) => (
                <td key={String(col.key)} className="px-4 py-3 text-zinc-300">
                  {col.render
                    ? col.render(row)
                    : String(row[col.key as keyof T] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
