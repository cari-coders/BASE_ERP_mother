import pickle
import base64

# Define a simple class
class MyClass:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"MyClass(name={self.name}, age={self.age})"

# Instance of MyClass
my_object = MyClass("John Doe", 30)

# Serialize the object to a string
serialized_str = base64.b64encode(pickle.dumps(my_object)).decode('utf-8')

# Deserialize the string back to an object
deserialized_object = pickle.loads(base64.b64decode(serialized_str.encode('utf-8')))

print("Serialized Object:", serialized_str)
print("Deserialized Object:", deserialized_object)

print(deserialized_object.name)

print(my_object is deserialized_object)