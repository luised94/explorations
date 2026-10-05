# total API calls
wc -l ~/conversations/api-calls.log

# calls per model
awk '{print $2}' ~/conversations/api-calls.log | sort | uniq -c | sort -rn

# total bytes sent (rough token proxy: bytes/4)
awk '{sum += $3} END {print sum " bytes, ~" int(sum/4) " tokens"}' ~/conversations/api-calls.log

# What actions do you actually take?
awk -F'\t' '{print $2}' ~/conversations/interaction-metrics.log | sort | uniq -c | sort -rn

# Which blocks get yanked/forked? (these are the "real" blocks)
awk -F'\t' '$2=="yank" || $2=="fork" {print $3}' ~/conversations/interaction-metrics.log | sort | uniq -c | sort -rn

# Navigation frequency (are you using ]m/[m or just scrolling?)
grep -c 'navigate' ~/conversations/interaction-metrics.log
