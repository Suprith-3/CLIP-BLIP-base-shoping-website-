import os

# Interactive script to setup Razorpay environment variables safely
key_id = input("Enter your Razorpay Key ID: ").strip()
key_secret = input("Enter your Razorpay Key Secret: ").strip()

if key_id and key_secret:
    with open('razorpay.env', 'w') as f:
        f.write(f"RAZORPAY_KEY_ID={key_id}\n")
        f.write(f"RAZORPAY_KEY_SECRET={key_secret}\n")
    print("razorpay.env file created successfully!")
else:
    print("Error: Credentials cannot be blank.")
