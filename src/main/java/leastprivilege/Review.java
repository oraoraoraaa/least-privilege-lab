package leastprivilege;

import java.io.PrintStream;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

final class Review {
    private static final class Evidence {
        boolean granted;
        long allowed;
        long denied;

        String finding() {
            if (!granted) {
                return allowed > 0 ? "historical-allow-outside-snapshot" : "denied-outside-snapshot";
            }
            if (allowed > 0) {
                return denied > 0 ? "mixed-history" : "observed-allow";
            }
            return denied > 0 ? "denied-history-only" : "unobserved";
        }
    }

    private final Map<Permission, Evidence> evidence = new TreeMap<>(Permission.ORDER);

    void grant(Permission permission) {
        evidence.computeIfAbsent(permission, ignored -> new Evidence()).granted = true;
    }

    void observe(Permission permission, boolean allowed) {
        Evidence row = evidence.computeIfAbsent(permission, ignored -> new Evidence());
        if (allowed) {
            row.allowed++;
        } else {
            row.denied++;
        }
    }

    void writeTo(PrintStream out) {
        out.println("principal\taction\tresource\tgranted_now\tallows\tdenies\tfinding");
        evidence.forEach((p, e) -> out.printf(Locale.ROOT, "%s\t%s\t%s\t%b\t%d\t%d\t%s%n",
            p.principal(), p.action(), p.resource(), e.granted, e.allowed, e.denied, e.finding()));
    }
}
