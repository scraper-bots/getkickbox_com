# Swift & iOS Development Essentials

> The essential 20% that will help you learn iOS development effectively.

This repository contains fundamental concepts and code examples for Swift and iOS development, focusing on the core 20% knowledge that will give you a strong foundation before learning the rest on the job.

## Table of Contents

- [Swift Language Fundamentals](#swift-language-fundamentals)
- [iOS Development Basics](#ios-development-basics)
- [Learning Resources](#learning-resources)
- [Project Ideas](#project-ideas)

## Swift Language Fundamentals

### 1. Basic Syntax and Data Types

Swift offers strong typing with type inference, making code both safe and concise:

```swift
// Variables and Constants
var mutableValue = 42          // Variable (can change)
let immutableValue = "Hello"   // Constant (cannot change)

// Basic Types
let integer: Int = 42
let decimal: Double = 3.14159
let text: String = "Hello, Swift!"
let isTrue: Bool = true

// Collections
let array = [1, 2, 3, 4, 5]
let dictionary = ["key1": "value1", "key2": "value2"]
let set: Set<String> = ["Apple", "Banana", "Orange"]

// Optionals
var optionalValue: String? = "Hello"
optionalValue = nil  // Valid because it's optional

// Unwrapping
if let unwrapped = optionalValue {
    print("Value exists: \(unwrapped)")
}
```

### 2. Control Flow

Swift provides modern control flow structures:

```swift
// If-Else
if score >= 90 {
    print("A grade")
} else if score >= 80 {
    print("B grade")
} else {
    print("Lower grade")
}

// Switch 
switch fruit {
case "Apple":
    print("It's an apple")
case "Orange", "Tangerine":
    print("It's an orange-like fruit")
default:
    print("It's something else")
}

// For-in Loops
for number in 1...5 {
    print(number)
}

// Guard (early exit)
guard let number = number, number > 0 else {
    print("Invalid number")
    return
}
```

### 3. Functions and Closures

Functions are first-class citizens in Swift:

```swift
// Basic Function
func greet(person: String) -> String {
    return "Hello, \(person)!"
}

// Default Parameters
func greet(person: String, message: String = "Hello") -> String {
    return "\(message), \(person)!"
}

// Closures
let doubled = [1, 2, 3].map { number in
    return number * 2
}
```

### 4. Object-Oriented Programming

Swift offers both classes (reference types) and structs (value types):

```swift
// Class
class Person {
    var name: String
    var age: Int
    
    init(name: String, age: Int) {
        self.name = name
        self.age = age
    }
    
    func introduce() {
        print("Hi, I'm \(name) and I'm \(age) years old.")
    }
}

// Struct
struct Point {
    var x: Double
    var y: Double
    
    mutating func moveBy(x deltaX: Double, y deltaY: Double) {
        x += deltaX
        y += deltaY
    }
}
```

### 5. Protocols and Extensions

These powerful features enable composition over inheritance:

```swift
// Protocol
protocol Identifiable {
    var id: String { get }
    func identify()
}

// Extension
extension String {
    func isValidEmail() -> Bool {
        return self.contains("@") && self.contains(".")
    }
}
```

## iOS Development Basics

### 1. UIKit Fundamentals

Understanding view controller lifecycle and basic UI components:

```swift
class MyViewController: UIViewController {
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
    }
    
    func setupUI() {
        let label = UILabel()
        label.text = "Hello iOS!"
        label.textAlignment = .center
        view.addSubview(label)
        
        // Auto Layout
        label.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
    }
}
```

### 2. Data Persistence

Simple ways to store data:

```swift
// UserDefaults
UserDefaults.standard.set("John", forKey: "username")
let username = UserDefaults.standard.string(forKey: "username")

// CoreData basics
let context = persistentContainer.viewContext
// Create, Read, Update, Delete operations
```

### 3. Networking

Making API requests:

```swift
func fetchData() {
    guard let url = URL(string: "https://api.example.com/data") else { return }
    
    URLSession.shared.dataTask(with: url) { (data, response, error) in
        guard let data = data, error == nil else { return }
        
        do {
            let json = try JSONDecoder().decode(MyModel.self, from: data)
            // Use decoded data
        } catch {
            print("Error: \(error)")
        }
    }.resume()
}
```

### 4. Common Design Patterns

Essential patterns in iOS development:

- **MVC**: Model-View-Controller
- **Delegation**: Passing responsibility between objects
- **Target-Action**: Responding to user interactions
- **Observer**: Notification of state changes

### 5. SwiftUI Basics

Modern declarative UI framework:

```swift
struct ContentView: View {
    @State private var count = 0
    
    var body: some View {
        VStack {
            Text("Count: \(count)")
                .font(.title)
            
            Button("Increment") {
                count += 1
            }
            .padding()
            .background(Color.blue)
            .foregroundColor(.white)
            .cornerRadius(10)
        }
    }
}
```

## Learning Resources

- [Swift Documentation](https://swift.org/documentation/)
- [Apple Developer - Swift](https://developer.apple.com/swift/)
- [Hacking with Swift](https://www.hackingwithswift.com/)
- [Ray Wenderlich](https://www.raywenderlich.com/)
- [Stanford CS193p](https://cs193p.sites.stanford.edu/)

## Project Ideas

Start with these simple projects to practice your skills:

1. **To-Do List App**: Learn about UITableView, data persistence
2. **Weather App**: Practice networking, JSON parsing, UI updates
3. **Photo Gallery**: Work with UICollectionView and the Photos framework
4. **Note Taking App**: Combine UI controls, CoreData, and text handling
5. **Simple Game**: Explore SpriteKit or simple game logic with UIKit

## Contributing

Feel free to submit pull requests with additional examples, clarifications, or fixes.

## License

This repository is available under the MIT License.
