# RCA: MusicBrainz mirror - recording Solr restore

**Status:** resolved on Mac shared-services host  
**Resolved:** 2026-05-30  
**Affects:** music provider `parsed` count (`generate_vibemon.py --provider music`, `MusicProvider.fetch`)

---

## Summary

The MusicBrainz mirror was healthy for Postgres-backed browse and direct lookup, but recording search returned no useful results. This broke the music provider because Last.fm often lacks valid recording MBIDs, and the provider falls back to `/ws/2/recording?query=...`.

The failure was in the `recording` Solr collection restore. The cached `recording.tar.zst` archive was valid, but the extracted backup tree under `/var/solr/data/backups/recording` was incomplete during earlier restore attempts. Solr restored from that incomplete tree, failed with missing index files, and left large stale `restore.*` directories under each live core.

The successful repair was:

1. Remove stale failed `restore.*` core directories.
2. Re-extract the valid `recording.tar.zst`.
3. Remove non-backup top-level files (`COPYING`, `README`) from the extracted restore path.
4. Submit a recording-only restore.
5. Recover from a disk-pressure/interrupted second restore by manually materializing valid shard index directories from the Solr backup metadata using hardlinks.
6. Point each core's `index.properties` at those durable manual directories.
7. Reload the `recording` collection.

Final state:

```text
recording_shard1_replica_n2 numDocs=9697624 size=18.47 GB directory=.../manual.20260530151957
recording_shard2_replica_n4 numDocs=9698160 size=19.73 GB directory=.../manual.20260530151957
recording_shard3_replica_n6 numDocs=9700188 size=18.5 GB  directory=.../manual.20260530151957
recording_shard4_replica_n1 numDocs=9700507 size=19.56 GB directory=.../manual.20260530151957
```

Search now works through both Solr and the MusicBrainz web API:

```json
{"count":8,"first":"Caraphernelia"}
```

---

## Impact

Before the fix, recording search returned zero:

```bash
docker compose exec -T search curl -s \
  'http://localhost:8983/solr/recording/advanced?q=recording:Caraphernelia&rows=3&wt=mbjson'
```

Observed result:

```json
{"count":0,"recordings":[]}
```

The music provider could still use some direct MBID paths, but most births were effectively blocked because many Last.fm tracks need MusicBrainz recording search as fallback. This showed up as a very low `parsed` count, for example `2/200`.

---

## What Was Ruled Out

| Layer | Finding |
| --- | --- |
| MusicBrainz web API | `:5000/ws/2/` was reachable from Mac and Windows |
| MusicBrainz Postgres | Real data was present in `musicbrainz_db`, not empty `musicbrainz` |
| Browse / lookup | Artist browse and direct MBID lookup worked; these use Postgres, not Solr search |
| Solr process | Collections existed and Solr was serving requests |
| Solr heap | Not the primary issue; restore failures were file/path related |
| Archive download integrity | `recording.tar.zst` passed MD5 and contained the allegedly missing files |
| Redis | Not involved until after Solr was fixed; Redis could only cache failed MusicBrainz responses |

Useful Postgres sanity check:

```bash
cd ~/infra/vibemon/deploy/musicbrainz-docker
docker compose exec db psql -U musicbrainz -d musicbrainz_db -t -c 'SELECT count(*) FROM musicbrainz.recording;'
```

---

## Root Cause

The root cause was an invalid restore source tree on disk, not a bad archive.

Solr logs from earlier attempts showed:

```text
Exception while restoring the backup index
Caused by: java.nio.file.NoSuchFileException:
  /var/solr/data/backups/recording/recording/index/8f805158-6655-4427-8241-3afb49087c30

Collection recording, operation restore failed => Could not restore core
```

But the archive contained the files:

```bash
cd /var/cache/musicbrainz/solr-backups
tar --use-compress-program=unzstd -tf recording.tar.zst |
  egrep '8f805158-6655-4427-8241-3afb49087c30|9faa45e3-24c3-4aa5-8809-9fb7067a8332'
```

Output included:

```text
recording/recording/index/8f805158-6655-4427-8241-3afb49087c30
recording/recording/index/9faa45e3-24c3-4aa5-8809-9fb7067a8332
```

The extracted backup tree was tiny and incomplete:

```text
/var/solr/data/backups/recording 96K
/var/solr/data/backups/recording/recording/index 68K
```

After manual extraction from the same archive, it became:

```text
/var/solr/data/backups/recording 77G
/var/solr/data/backups/recording/recording/index 77G
```

That proves the archive was valid and the failure was caused by stale/incomplete extracted restore data.

---

## Contributing Factors

### The helper has no collection filter

`load-backup-archives --help` supports only environment variables:

```text
MUSICBRAINZ_SEARCH_DUMP_DIR
SOLR_BACKUPS_DIR
SOLR_LOCAL_HOST
SOLR_PORT
```

It loops over every `*.tar.zst` in the dump directory. Because we needed a recording-only restore, running the helper directly against the full archive directory was not appropriate.

### Manual extraction included non-backup files

Extracting the full archive into `/var/solr/data/backups` included:

```text
/var/solr/data/backups/recording/COPYING
/var/solr/data/backups/recording/README
```

Direct Solr restore failed on that shape:

```json
{
  "status": 500,
  "msg": "/var/solr/data/backups/recording/COPYING"
}
```

The helper avoids this because it extracts only `recording/recording`, not the whole archive payload.

### Synchronous restore timed out after doing useful work

The first direct restore returned:

```text
restore the collection time out:180s
```

But it had actually activated the restored data. Core status later showed ~9.7M docs per shard and search worked. The 180s API timeout should not be treated as definitive failure without checking core status and search.

### A second restore under disk pressure created a bad mixed state

After the first restore, a second async restore was submitted while the first restored index was already active. During that second restore, disk filled:

```text
java.io.IOException: No space left on device
```

That failed restore left large incomplete `restore.20260530145152...` directories. Worse, cleanup had removed the first active `restore.202605301446...` contents after Solr had already activated them, leaving only `write.lock` in the paths referenced by `index.properties`.

At that point:

```text
index.properties -> restore.202605301446...
restore.202605301446... -> only write.lock
search still worked because Solr had the index open
reload/restart would fail because no segments_* file existed in the referenced directory
```

This was recovered before restart by creating durable manual index directories and repointing `index.properties`.

---

## Recovery Steps Taken

### 1. Verified the archive extracted correctly

```bash
cd ~/infra/vibemon/deploy/musicbrainz-docker

docker compose exec -T search sh -lc '
set -eu

df -h /var/solr /var/cache/musicbrainz
rm -rf /var/solr/data/backups/recording

cd /var/solr/data/backups
tar --use-compress-program=unzstd -xf /var/cache/musicbrainz/solr-backups/recording.tar.zst

ls -lh \
  /var/solr/data/backups/recording/recording/index/8f805158-6655-4427-8241-3afb49087c30 \
  /var/solr/data/backups/recording/recording/index/9faa45e3-24c3-4aa5-8809-9fb7067a8332

du -h -d 3 /var/solr/data/backups/recording | sort -h | tail -30
df -h /var/solr /var/cache/musicbrainz
'
```

Result:

```text
/var/solr/data/backups/recording/recording/index/... existed
/var/solr/data/backups/recording 77G
```

### 2. Removed stale failed restore directories

The active cores still served tiny `/index` directories, so old `restore.*` directories were stale and safe to remove.

```bash
docker compose exec -T search sh -lc '
set -eu

for core in recording_shard1_replica_n2 recording_shard2_replica_n4 recording_shard3_replica_n6 recording_shard4_replica_n1; do
  curl -s "http://localhost:8983/solr/admin/cores?action=STATUS&core=$core&wt=json" |
    grep -E "\"numDocs\"|\"directory\"|\"size\"|\"lastModified\""
done

find /var/solr/data/data -maxdepth 2 -type d \
  -path "/var/solr/data/data/recording_shard*_replica_n*/restore.*" \
  -prune -print -exec rm -rf {} \;

df -h /var/solr
'
```

Disk improved from `36G` free to `134G` free.

### 3. Inspected restore helper behavior

The helper effectively does:

```bash
curl -sS \
  "$SOLR_BASE_URL/solr/admin/collections?action=RESTORE&collection=$collection&name=$collection&location=$SOLR_BACKUPS_DIR"
```

and extracts:

```bash
tar -x --zstd -f "$DUMP_DIR/$dump_file" -C "$SOLR_BACKUPS_DIR" "$collection/$collection"
```

That explained why full manual extraction caused the `COPYING` error.

### 4. Removed non-backup top-level files

```bash
docker compose exec -T search sh -lc '
set -eu

find /var/solr/data/backups/recording -mindepth 1 -maxdepth 1 ! -name recording -print -exec rm -rf {} \;
find /var/solr/data/backups/recording -maxdepth 2 -mindepth 1 -print | head -30
'
```

After cleanup, the backup shape was:

```text
/var/solr/data/backups/recording/recording
/var/solr/data/backups/recording/recording/shard_backup_metadata
/var/solr/data/backups/recording/recording/zk_backup_0
/var/solr/data/backups/recording/recording/index
/var/solr/data/backups/recording/recording/backup_0.properties
```

### 5. Submitted recording-only restore

```bash
docker compose exec -T search sh -lc '
set -eu

curl -sS \
  "http://localhost:8983/solr/admin/collections?action=RESTORE&collection=recording&name=recording&location=/var/solr/data/backups" |
  jq .
'
```

This returned a 180s timeout, but later evidence showed the first restore had activated:

```text
recording_shard1_replica_n2 numDocs=9697624 directory=.../restore.20260530144624156
recording_shard2_replica_n4 numDocs=9698160 directory=.../restore.20260530144624157
recording_shard3_replica_n6 numDocs=9700188 directory=.../restore.20260530144624155
recording_shard4_replica_n1 numDocs=9700507 directory=.../restore.20260530144624155
```

### 6. Recovered durable index directories after disk-pressure incident

Because the active `index.properties` pointed at directories whose contents had been removed, durable manual directories were reconstructed from the extracted backup metadata.

Important mechanics:

- Solr backup files are stored by backup object ID under `recording/recording/index`.
- Each shard has a metadata map under `recording/recording/shard_backup_metadata/md_shardN_0.json`.
- The metadata maps backup object IDs to Lucene filenames.
- Hardlinking the backup objects into a per-core directory under their Lucene filenames creates a valid index directory without doubling disk usage.

Recovery command used:

```bash
cd ~/infra/vibemon/deploy/musicbrainz-docker

docker compose exec -T search sh -lc '
set -eu

BACKUP_ROOT=/var/solr/data/backups/recording
BACKUP_ARCHIVE=/var/cache/musicbrainz/solr-backups/recording.tar.zst
TARGET="manual.$(date +%Y%m%d%H%M%S)"

rm -rf /var/solr/data/data/recording_shard1_replica_n2/restore.20260530145152888
rm -rf /var/solr/data/data/recording_shard2_replica_n4/restore.20260530145152886
rm -rf /var/solr/data/data/recording_shard3_replica_n6/restore.20260530145152889
rm -rf /var/solr/data/data/recording_shard4_replica_n1/restore.20260530145152891

rm -rf "$BACKUP_ROOT"
mkdir -p /var/solr/data/backups
tar -x --zstd -f "$BACKUP_ARCHIVE" -C /var/solr/data/backups recording/recording

build_core() {
  core="$1"
  shard="$2"
  target_dir="/var/solr/data/data/$core/$TARGET"
  metadata="$BACKUP_ROOT/recording/shard_backup_metadata/md_${shard}_0.json"
  backup_index="$BACKUP_ROOT/recording/index"

  rm -rf "$target_dir"
  mkdir -p "$target_dir"

  jq -r "to_entries[] | [.key, .value.fileName] | @tsv" "$metadata" |
    while IFS="$(printf "\t")" read -r backup_id file_name; do
      test -f "$backup_index/$backup_id"
      ln "$backup_index/$backup_id" "$target_dir/$file_name"
    done

  test "$(find "$target_dir" -maxdepth 1 -type f -name "segments_*" | wc -l)" -gt 0

  printf "#index.properties\n#manual recovery\nindex=%s\n" "$TARGET" > "/var/solr/data/data/$core/index.properties.next"
  mv "/var/solr/data/data/$core/index.properties.next" "/var/solr/data/data/$core/index.properties"
}

build_core recording_shard1_replica_n2 shard1
build_core recording_shard2_replica_n4 shard2
build_core recording_shard3_replica_n6 shard3
build_core recording_shard4_replica_n1 shard4

curl -sS "http://localhost:8983/solr/admin/collections?action=RELOAD&name=recording&wt=json" | jq .
'
```

Manual directory created:

```text
manual.20260530151957
```

Reload succeeded:

```json
{
  "responseHeader": {"status": 0},
  "success": {
    "172.20.0.2:8983_solr": {
      "responseHeader": {"status": 0}
    }
  }
}
```

### 7. Cleaned leftover extracted backup and stale dirs

After status pointed at `manual.20260530151957`, cleanup removed only non-active leftovers:

```bash
docker compose exec -T search sh -lc '
set -eu

rm -rf /var/solr/data/backups/recording
rm -rf /var/solr/data/data/recording_shard1_replica_n2/restore.20260530144624156
rm -rf /var/solr/data/data/recording_shard2_replica_n4/restore.20260530144624157
rm -rf /var/solr/data/data/recording_shard3_replica_n6/restore.20260530144624155
rm -rf /var/solr/data/data/recording_shard4_replica_n1/restore.20260530144624155

df -h /var/solr
'
```

Final disk:

```text
/dev/vdb1 394G 243G 134G 65% /var/solr
```

---

## Final Verification

Core status:

```text
recording_shard1_replica_n2 numDocs=9697624 directory=.../manual.20260530151957 size=18.47 GB
recording_shard2_replica_n4 numDocs=9698160 directory=.../manual.20260530151957 size=19.73 GB
recording_shard3_replica_n6 numDocs=9700188 directory=.../manual.20260530151957 size=18.5 GB
recording_shard4_replica_n1 numDocs=9700507 directory=.../manual.20260530151957 size=19.56 GB
```

Solr search:

```bash
docker compose exec -T search curl -s \
  'http://localhost:8983/solr/recording/advanced?q=recording:Caraphernelia&rows=3&wt=mbjson'
```

Result:

```json
{"count":8}
```

MusicBrainz web API search:

```bash
curl -sG 'http://127.0.0.1:5000/ws/2/recording' \
  --data-urlencode 'query=recording:Caraphernelia' \
  --data-urlencode 'limit=3' \
  --data-urlencode 'fmt=json' |
  jq '{count, first: .recordings[0].title}'
```

Result:

```json
{
  "count": 8,
  "first": "Caraphernelia"
}
```

---

## Recurrence Risk

This can happen again if we repeat the same restore workflow under the same constraints.

High-risk patterns:

- Running restore while `/var/solr` does not have enough free space for both the extracted backup and temporary restore directories.
- Treating a 180s Solr collection-admin timeout as definite failure and immediately launching another restore.
- Deleting any `restore.*` directory after Solr has activated it.
- Manually extracting the whole archive instead of only `recording/recording`.
- Running `load-backup-archives` against a directory containing all collection archives when only one collection needs repair.

The biggest structural risk is disk headroom. During this incident:

- Extracted recording backup used ~77G.
- Active restored recording cores used ~76G.
- A second restore could create another ~76G of temporary restore directories.

A 394G volume had enough space for one careful recording restore, but not enough for repeated attempts plus extracted backup trees and stale restore directories.

---

## Prevention

Before any future Solr restore:

1. Confirm free space.

   ```bash
   docker compose exec -T search df -h /var/solr /var/cache/musicbrainz
   ```

2. Confirm active core directories before deleting anything.

   ```bash
   docker compose exec -T search sh -lc '
   for core in recording_shard1_replica_n2 recording_shard2_replica_n4 recording_shard3_replica_n6 recording_shard4_replica_n1; do
     echo "=== $core ==="
     curl -s "http://localhost:8983/solr/admin/cores?action=STATUS&core=$core&wt=json" |
       grep -E "\"numDocs\"|\"directory\"|\"size\"|\"lastModified\""
   done
   '
   ```

3. Delete only inactive stale restore directories.

4. If restoring one collection, either:

   - use a temp dump directory containing only that collection's archive, or
   - manually extract only the collection backup payload:

     ```bash
     tar -x --zstd -f /var/cache/musicbrainz/solr-backups/recording.tar.zst \
       -C /var/solr/data/backups recording/recording
     ```

5. If a restore times out, inspect before retrying:

   ```bash
   docker compose exec -T search sh -lc '
   for core in recording_shard1_replica_n2 recording_shard2_replica_n4 recording_shard3_replica_n6 recording_shard4_replica_n1; do
     echo "=== $core ==="
     curl -s "http://localhost:8983/solr/admin/cores?action=STATUS&core=$core&wt=json" |
       grep -E "\"numDocs\"|\"directory\"|\"size\"|\"lastModified\""
   done
   curl -s "http://localhost:8983/solr/recording/advanced?q=recording:Caraphernelia&rows=1&wt=mbjson" |
     jq "{count, first: .recordings[0].title}"
   '
   ```

6. Do not restart Solr if `index.properties` points to a directory without `segments_*`.

   ```bash
   docker compose exec -T search sh -lc '
   for core in recording_shard1_replica_n2 recording_shard2_replica_n4 recording_shard3_replica_n6 recording_shard4_replica_n1; do
     index="$(sed -n "s/^index=//p" "/var/solr/data/data/$core/index.properties")"
     echo "=== $core -> $index ==="
     find "/var/solr/data/data/$core/$index" -maxdepth 1 -type f -name "segments_*" -print
   done
   '
   ```

---

## Do Not Re-Debug

- Do not redownload archives just because `recording` search is empty. The cached `recording.tar.zst` was valid.
- Do not chase Postgres database name again. The populated DB is `musicbrainz_db`.
- Do not use `docker compose run search ...` for Solr operations. Use `docker compose up -d search`, then `docker compose exec ...`.
- Do not query Solr counts with only `/select?q=*:*` and assume that proves emptiness. This MusicBrainz Solr config uses custom handlers; core `STATUS` and real `/advanced` search are better gates.
- Do not run a second restore immediately after a timeout. First check active core status, `index.properties`, disk, and search.
- Do not delete any active directory named in core `STATUS` or `index.properties`.
