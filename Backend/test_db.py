from app.database.connection import engine
print("Step 1")


print("Step 2")

try:
    connection = engine.connect()
    print("✅ Database Connected Successfully!")
    connection.close()
except Exception as e:
    print("Error:", e)

print("Step 3")
