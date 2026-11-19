package leastprivilege;

record Permission(String principal, String action, String resource) {
    Permission {
        for (String value : new String[] { principal, action, resource }) {
            if (value.isBlank() || !value.equals(value.strip()) || value.contains("*")) {
                throw new IllegalArgumentException("expected a concrete, nonblank identifier without padding or '*'");
            }
        }
    }
}
