package leastprivilege;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.function.Consumer;

final class Inputs {
    static void readGrants(Path path, Review review) throws IOException {
        readRows(path, Permission.HEADER, fields ->
            review.grant(new Permission(fields[0], fields[1], fields[2])));
    }

    static void readEvents(Path path, Review review) throws IOException {
        readRows(path, "timestamp\tprincipal\taction\tresource\tdecision", fields -> {
            try {
                Instant.parse(fields[0]);
            } catch (DateTimeParseException e) {
                throw new IllegalArgumentException("invalid ISO-8601 timestamp");
            }
            var permission = new Permission(fields[1], fields[2], fields[3]);
            switch (fields[4]) {
                case "ALLOW" -> review.observe(permission, true);
                case "DENY" -> review.observe(permission, false);
                default -> throw new IllegalArgumentException("expected ALLOW or DENY");
            }
        });
    }

    static void readRows(Path path, String header, Consumer<String[]> accept) throws IOException {
        int columns = header.split("\t").length;
        try (BufferedReader reader = Files.newBufferedReader(path)) {
            if (!header.equals(reader.readLine())) {
                throw new IOException(path + ":1: expected header " + header);
            }
            int lineNumber = 1;
            String line;
            while ((line = reader.readLine()) != null) {
                lineNumber++;
                String[] fields = line.split("\t", -1);
                if (fields.length != columns) {
                    throw new IOException(path + ":" + lineNumber + ": expected " + columns + " columns");
                }
                try {
                    accept.accept(fields);
                } catch (IllegalArgumentException e) {
                    throw new IOException(path + ":" + lineNumber + ": " + e.getMessage(), e);
                }
            }
        }
    }
}
