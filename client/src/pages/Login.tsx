import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MessageSquare, ArrowRight, Sparkles } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCheckAvailability } from "@/hooks/use-users";
import { useToast } from "@/hooks/use-toast";

const loginSchema = z.object({
  username: z
    .string()
    .min(3, "Username must be at least 3 characters")
    .max(20, "Username must be less than 20 characters")
    .regex(/^[a-zA-Z0-9_]+$/, "Only letters, numbers, and underscores allowed"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

interface LoginProps {
  onJoin: (username: string) => void;
}

export default function Login({ onJoin }: LoginProps) {
  const [isChecking, setIsChecking] = useState(false);
  const { toast } = useToast();
  const checkAvailability = useCheckAvailability();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setIsChecking(true);
    try {
      // First check if user exists logic could go here if we were persisting users
      // For this ephemeral chat, we just proceed directly or check conflicts
      const result = await checkAvailability.mutateAsync(data.username);
      
      if (result.available) {
        onJoin(data.username);
      } else {
        form.setError("username", {
          type: "manual",
          message: "This username is already taken by an active user.",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to connect. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-background via-muted/50 to-primary/5 p-4">
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none"></div>
      
      <div className="w-full max-w-md animate-slide-up relative z-10">
        <div className="mb-8 text-center space-y-2">
          <div className="mx-auto w-16 h-16 bg-gradient-to-tr from-primary to-violet-400 rounded-2xl flex items-center justify-center shadow-lg shadow-primary/20 rotate-3 transition-transform hover:rotate-6 duration-300">
            <MessageSquare className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
            ChatRoom
          </h1>
          <p className="text-muted-foreground text-lg">
            Connect with friends in real-time.
          </p>
        </div>

        <Card className="border-border/50 shadow-xl shadow-black/5 backdrop-blur-sm bg-card/80">
          <CardHeader>
            <CardTitle>Welcome Back</CardTitle>
            <CardDescription>
              Enter a username to join the global chat channel.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Username</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Input
                            placeholder="johndoe"
                            className="pl-10 h-12 bg-background/50 border-input/50 focus:bg-background transition-all"
                            {...field}
                          />
                          <Sparkles className="absolute left-3 top-3.5 h-5 w-5 text-muted-foreground" />
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <Button
                  type="submit"
                  className="w-full h-12 text-base font-semibold shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all"
                  disabled={isChecking || checkAvailability.isPending}
                >
                  {isChecking || checkAvailability.isPending ? (
                    "Checking availability..."
                  ) : (
                    <>
                      Join Chat <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>
            </Form>
          </CardContent>
          <CardFooter className="justify-center border-t bg-muted/30 py-4">
            <p className="text-xs text-muted-foreground text-center">
              By joining, you agree to be nice and respectful.
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
