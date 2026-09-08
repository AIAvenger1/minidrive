import type { SyncReport } from '@minidrive/shared';
import { Alert, AlertDescription } from './components/ui/alert';

export function SyncReportSummary({ report }: { report: SyncReport }) {
  return (
    <Alert className="w-full">
      <AlertDescription>
        Надіслано {report.uploaded}, скачано {report.downloaded}, пропущено {report.skipped}, помилок{' '}
        {report.failed}
      </AlertDescription>
    </Alert>
  );
}
