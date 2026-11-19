package leastprivilege;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

public final class Main {
    private static final String USAGE = """
        Usage: java -jar least-privilege-lab.jar review GRANTS.tsv EVENTS.tsv
               java -jar least-privilege-lab.jar group-grants MEMBERSHIPS.tsv GROUP_GRANTS.tsv""";

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--help")) {
            System.out.println(USAGE);
            return;
        }
        if (args.length != 3 || !(args[0].equals("review") || args[0].equals("group-grants"))) {
            System.err.println(USAGE);
            System.exit(2);
        }
        try {
            var output = new PrintStream(System.out, true, StandardCharsets.UTF_8);
            if (args[0].equals("group-grants")) {
                GroupGrants.expand(Path.of(args[1]), Path.of(args[2]), output);
            } else {
                var review = new Review();
                Inputs.readGrants(Path.of(args[1]), review);
                Inputs.readEvents(Path.of(args[2]), review);
                review.writeTo(output);
            }
            if (output.checkError()) {
                throw new IOException("could not write the complete report");
            }
        } catch (IOException | IllegalArgumentException e) {
            System.err.println("Review failed: " + e.getMessage());
            System.exit(1);
        }
    }
}
