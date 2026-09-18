import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getJob, type JobStatus } from "../api/client";

const POLL_MS = 700;

export interface JobRun {
  status: JobStatus | null;
  error: string | null;
  running: boolean;
  /** İşi başlatır ve bitene kadar durumunu izler. */
  start: (begin: () => Promise<JobStatus>) => Promise<JobStatus | null>;
  reset: () => void;
}

/** Arka plan işini başlatır ve tamamlanana kadar durumunu yoklar. */
export function useJob(): JobRun {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    return () => {
      cancelled.current = true;
    };
  }, []);

  const start = useCallback(async (begin: () => Promise<JobStatus>) => {
    setError(null);
    setRunning(true);
    try {
      let current = await begin();
      setStatus(current);
      while (current.state === "queued" || current.state === "running") {
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
        if (cancelled.current) return null;
        current = await getJob(current.id);
        setStatus(current);
      }
      if (current.state === "error") setError(current.error_tr ?? "bilinmeyen hata");
      return current;
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : String(cause));
      return null;
    } finally {
      if (!cancelled.current) setRunning(false);
    }
  }, []);

  const reset = useCallback(() => {
    setStatus(null);
    setError(null);
  }, []);

  return { status, error, running, start, reset };
}
