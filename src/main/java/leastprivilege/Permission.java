package leastprivilege;

import java.util.Comparator;

record Permission(String principal, String action, String resource) {
    static final String HEADER = "principal\taction\tresource";
    static final Comparator<Permission> ORDER = Comparator.comparing(Permission::principal)
        .thenComparing(Permission::action).thenComparing(Permission::resource);

    Permission {
        checkId(principal);
        checkId(action);
        checkId(resource);
    }

    static void checkId(String value) {
        if (value.isBlank() || !value.equals(value.strip()) || value.contains("*")) {
            throw new IllegalArgumentException("expected a concrete, nonblank identifier without padding or '*'");
        }
    }
}
