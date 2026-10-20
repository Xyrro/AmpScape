#!/bin/bash
# Review round 3: throttled submission of the remaining solve shards under the QoS limit of 50 submitted jobs per
# user, keeping this work at <= MAXMINE jobs and >= 10 free slots for the owner's other projects.
# Stop: kill "$(cat aux/review_round3/logs/r3_submitter.pid)"  (pid file only; never by name pattern).
cd /storage/ice1/1/8/yxiao413/EcoFlowBench
echo $$ > aux/review_round3/logs/r3_submitter.pid
MAXMINE=${MAXMINE:-30}
Q=aux/review_round3/logs/submit_queue.txt     # lines: name build lo hi mem time   (consumed from the top)
LOG=aux/review_round3/logs/submissions.txt
while [ -s "$Q" ]; do
  all=$(squeue -u "$USER" -r -h | wc -l)
  mine=$(squeue -u "$USER" -r -h -o "%j" | grep -c '^r3-')
  free=$(( 40 - all )); room=$(( MAXMINE - mine )); [ $room -lt $free ] && free=$room
  if [ "$free" -gt 0 ]; then
    read -r name build lo hi mem tm < "$Q"
    n=$(( hi - lo + 1 )); [ $n -gt $free ] && n=$free
    top=$(( lo + n - 1 ))
    if j=$(sbatch --parsable -J "r3-solve-$name" --array=$lo-$top --mem=$mem -t $tm -o "$build/logs/%A_%a.out" \
           --export=ALL,BUILD=$build scripts/review/r3_solve.sbatch 2>&1); then
      echo "$name $lo-$top $j $(date -u +%FT%TZ)" >> $LOG
      # rewrite the queue head without sed (build paths contain '/'; a sed s/// here re-submitted shards, 2026-10-20)
      { [ $top -lt $hi ] && echo "$name $build $((top+1)) $hi $mem $tm"; tail -n +2 "$Q"; } > "$Q.tmp" && mv "$Q.tmp" "$Q"
    else
      echo "submit failed $name $lo-$top: $j" >> $LOG
    fi
  fi
  sleep 300
done
echo "queue empty $(date -u +%FT%TZ)" >> $LOG
rm -f aux/review_round3/logs/r3_submitter.pid
