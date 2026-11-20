package app.cash.zipline.loader.internal.cache.ziplineloader;

import app.cash.zipline.loader.internal.cache.Database;
import app.cash.zipline.loader.internal.cache.Files;
import com.squareup.sqldelight.ColumnAdapter;
import com.squareup.sqldelight.Query;
import com.squareup.sqldelight.db.SqlCursor;
import com.squareup.sqldelight.db.SqlDriver;
import com.squareup.sqldelight.db.SqlPreparedStatement;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import kotlin.Unit;
import kotlin.jvm.functions.Function1;

/** Observe the released implementation at its SQL driver interface. */
public final class ReleaseQueries {
    private static String current;

    @SuppressWarnings("unchecked")
    private static <T> T proxy(Class<T> type, java.lang.reflect.InvocationHandler handler) {
        return (T) Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, handler);
    }

    private static String encode(String s) {
        return Base64.getEncoder().encodeToString(s.getBytes(StandardCharsets.UTF_8));
    }

    private static void record(String name, Query<?> query) throws java.io.IOException {
        current = name;
        query.execute().close();
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws java.io.IOException {
        SqlDriver driver = proxy(SqlDriver.class, (obj, method, values) -> {
            if (!method.getName().equals("executeQuery")) throw new AssertionError(method);
            String[] bindings = new String[(Integer) values[2]];
            if (values[3] != null) {
                SqlPreparedStatement stmt = proxy(SqlPreparedStatement.class, (o, m, pair) -> {
                    int index = (Integer) pair[0] - 1;
                    Object value = pair[1];
                    bindings[index] = value == null ? "N" : value instanceof Number ? "I" + value : "S" + encode(value.toString());
                    return null;
                });
                ((Function1<SqlPreparedStatement, Unit>) values[3]).invoke(stmt);
            }
            if (Arrays.asList(bindings).contains(null)) throw new AssertionError(current);
            System.out.println(current + "\t" + encode((String) values[1]) + "\t" + String.join(",", bindings));
            return proxy(SqlCursor.class, (o, m, v) -> null);
        });
        ColumnAdapter<?, ?> adapter = proxy(ColumnAdapter.class, (o, m, v) -> {throw new AssertionError(m);});
        Database db = new DatabaseImpl(driver, new Files.Adapter((ColumnAdapter) adapter));
        var f = db.getFilesQueries();
        var p = db.getPinsQueries();
        record("Files.selectCacheSumBytes", f.selectCacheSumBytes());
        record("Files.count", f.count());
        record("Files.get", f.get("test"));
        record("Files.getById", f.getById(1));
        record("Files.selectOldestReady", f.selectOldestReady());
        record("Files.selectAnyDirtyFile", f.selectAnyDirtyFile());
        for (String name : new String[]{"test", null}) {
            String shape = name == null ? "/null" : "/value";
            record("Files.selectPinnedManifest" + shape, f.selectPinnedManifest(name));
            record("Files.selectPinnedManifestNotFileId" + shape, f.selectPinnedManifestNotFileId(name, 1));
        }
        record("Pins.count", p.count());
        record("Pins.get_pin", p.get_pin(1, "test"));
    }
}
