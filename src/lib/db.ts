// lib/db.ts
import Database from 'better-sqlite3';

export function openDb() {
  const db = new Database('/Users/muhamamdnurasid/Documents/Semester_4/Softw_Eng/Ehee/Traffic-Monitoring/traffic_monitor_data.db');
  return db;
}
