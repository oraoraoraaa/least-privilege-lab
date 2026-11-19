package leastprivilege;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeSet;

final class GroupGrants {
    static void expand(Path memberships, Path groupGrants, PrintStream output) throws IOException {
        var members = new HashMap<String, Set<String>>();
        Inputs.readRows(memberships, "principal\tgroup", fields -> {
            Permission.checkId(fields[0]);
            Permission.checkId(fields[1]);
            members.computeIfAbsent(fields[1], ignored -> new HashSet<>()).add(fields[0]);
        });

        var grants = new TreeSet<>(Permission.ORDER);
        Inputs.readRows(groupGrants, "group\taction\tresource", fields -> {
            for (String field : fields) {
                Permission.checkId(field);
            }
            for (String principal : members.getOrDefault(fields[0], Set.of())) {
                grants.add(new Permission(principal, fields[1], fields[2]));
            }
        });

        output.println(Permission.HEADER);
        for (Permission grant : grants) {
            output.println(grant.principal() + "\t" + grant.action() + "\t" + grant.resource());
        }
    }
}
